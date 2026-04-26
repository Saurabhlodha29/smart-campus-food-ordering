"""
models/demand_forecast.py — Slot demand forecasting for outlet managers.

Algorithm: Statsmodels SARIMA (Seasonal ARIMA) as primary,
           with a simple hourly-average fallback.

WHY SARIMA OVER PROPHET?
  - Prophet requires facebook/prophet which has complex dependencies (pystan,
    cmdstanpy) that are hard to install on free-tier cloud servers.
  - Statsmodels is already in the ML ecosystem (no extra deps).
  - SARIMA handles weekly + daily seasonality well for campus patterns.
  - For production with more data, switch to Prophet — just swap the fit() method.

SEASONALITY: 
  Campus food ordering has strong weekly seasonality (Monday ≠ Saturday)
  and daily seasonality (rush at 12–1 PM, quiet at 3–4 PM).

FALLBACK: if SARIMA fails (not enough data / convergence issues), we return
  a day-of-week × hour_of_day lookup table built from raw averages.
  This is always reliable, just not forward-looking.

OUTPUT per hour: predictedOrders (int), suggestedSlotCapacity (int)
  suggestedSlotCapacity = round(predictedOrders × 1.15)  [15% buffer]
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

SLOT_BUFFER = 1.15          # allow 15% more than predicted
MIN_DATA_WEEKS = 2          # need at least 2 weeks of data for SARIMA


class DemandForecastModel:
    """
    Per-outlet demand forecasting model.
    One instance is created and cached per outlet_id.
    """

    def __init__(self, outlet_id: int):
        self.outlet_id = outlet_id
        self.sarima_model = None
        self.hourly_avg: Optional[pd.DataFrame] = None   # fallback lookup
        self.is_fitted = False
        self.strategy_used = "none"

    def fit(self, series_df: pd.DataFrame) -> dict:
        """
        Fit the forecasting model on historical load series.

        Args:
            series_df: from get_outlet_load_series() — columns: ds, y, hour_of_day, day_of_week

        Returns: dict with training metadata
        """
        if series_df.empty or len(series_df) < 24:
            logger.warning("[forecast outlet=%s] Not enough data", self.outlet_id)
            return {"status": "insufficient_data"}

        series_df = series_df.copy()
        series_df["ds"] = pd.to_datetime(series_df["ds"])
        series_df = series_df.sort_values("ds")

        # ── Always build the hourly average lookup (used as fallback) ──────
        self.hourly_avg = (
            series_df.groupby(["day_of_week", "hour_of_day"])["y"]
            .mean()
            .reset_index()
            .rename(columns={"y": "avg_orders"})
        )

        # ── Try SARIMA on hourly time series ───────────────────────────────
        weeks_of_data = (series_df["ds"].max() - series_df["ds"].min()).days / 7

        if weeks_of_data >= MIN_DATA_WEEKS:
            try:
                from statsmodels.tsa.statespace.sarimax import SARIMAX

                # Resample to hourly grid — fill missing hours with 0
                ts = series_df.set_index("ds")["y"].resample("h").sum().fillna(0)

                # SARIMA(1,0,1)(1,1,1)[24] — daily seasonality
                # P,D,Q = seasonal AR, I, MA
                # m = 24 hours per day (seasonal period)
                # We use a simple specification to avoid convergence issues
                # on limited data; tune P,D,Q for production
                sarima = SARIMAX(
                    ts,
                    order=(1, 0, 1),
                    seasonal_order=(1, 1, 1, 24),
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                fit = sarima.fit(disp=False, maxiter=50)
                self.sarima_model = fit
                self.strategy_used = "sarima"
                logger.info(
                    "[forecast outlet=%s] SARIMA fitted | AIC=%.2f",
                    self.outlet_id, fit.aic
                )
            except Exception as exc:
                logger.warning("[forecast outlet=%s] SARIMA failed (%s) — using averages", self.outlet_id, exc)
                self.strategy_used = "hourly_averages"
        else:
            logger.info(
                "[forecast outlet=%s] Only %.1f weeks of data — using averages",
                self.outlet_id, weeks_of_data
            )
            self.strategy_used = "hourly_averages"

        self.is_fitted = True
        return {
            "status": "trained",
            "strategy": self.strategy_used,
            "n_hourly_points": len(series_df),
        }

    def forecast_day(self, date: "datetime.date") -> list[dict]:
        """
        Predict order counts for every hour of a specific date.

        Returns: list of 24 dicts, one per hour
            [{"hour": 0, "predictedOrders": 3, "suggestedSlotCapacity": 4}, ...]
        """
        import datetime as dt
        day_of_week = date.weekday()  # 0=Mon, 6=Sun → match Python convention
        # Postgres DOW: 0=Sun, 1=Mon...6=Sat; we used Python below for consistency

        if not self.is_fitted:
            return self._empty_forecast()

        # ── SARIMA forecast ────────────────────────────────────────────────
        if self.sarima_model is not None and self.strategy_used == "sarima":
            try:
                target_start = pd.Timestamp(date)
                target_end = target_start + pd.Timedelta(hours=23)
                forecast = self.sarima_model.predict(
                    start=target_start, end=target_end
                )
                result = []
                for hour in range(24):
                    ts = target_start + pd.Timedelta(hours=hour)
                    predicted = max(0, round(float(forecast.get(ts, 0))))
                    capacity = max(1, round(predicted * SLOT_BUFFER))
                    result.append({
                        "hour": hour,
                        "predictedOrders": predicted,
                        "suggestedSlotCapacity": capacity,
                    })
                return result
            except Exception as exc:
                logger.warning("[forecast] SARIMA predict failed (%s) — fallback to averages", exc)

        # ── Hourly average fallback ────────────────────────────────────────
        return self._average_forecast(day_of_week)

    def get_peak_hours(self) -> dict:
        """
        Return peak and off-peak hours based on historical averages.
        A "peak" hour is above the 70th percentile of hourly order counts.
        """
        if self.hourly_avg is None or self.hourly_avg.empty:
            return {"peakHours": [12, 13, 18], "lowHours": [9, 10, 15]}

        by_hour = self.hourly_avg.groupby("hour_of_day")["avg_orders"].mean()
        if by_hour.empty:
            return {"peakHours": [12, 13, 18], "lowHours": [9, 10, 15]}

        p70 = by_hour.quantile(0.70)
        p30 = by_hour.quantile(0.30)

        peak_hours = sorted(by_hour[by_hour >= p70].index.tolist())
        low_hours = sorted(by_hour[by_hour <= p30].index.tolist())

        return {
            "peakHours": [int(h) for h in peak_hours],
            "lowHours": [int(h) for h in low_hours],
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _average_forecast(self, day_of_week: int) -> list[dict]:
        """Use the hourly average lookup table for the given day_of_week."""
        result = []
        # Convert Python weekday (0=Mon) to Postgres DOW (0=Sun)
        pg_dow = (day_of_week + 1) % 7

        for hour in range(24):
            mask = (
                (self.hourly_avg["day_of_week"] == pg_dow) &
                (self.hourly_avg["hour_of_day"] == hour)
            )
            rows = self.hourly_avg[mask]
            predicted = max(0, round(float(rows["avg_orders"].iloc[0]))) if not rows.empty else 0
            capacity = max(1, round(predicted * SLOT_BUFFER))
            result.append({
                "hour": hour,
                "predictedOrders": predicted,
                "suggestedSlotCapacity": capacity,
            })
        return result

    @staticmethod
    def _empty_forecast() -> list[dict]:
        return [
            {"hour": h, "predictedOrders": 0, "suggestedSlotCapacity": 5}
            for h in range(24)
        ]