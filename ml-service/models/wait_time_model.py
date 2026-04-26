"""
models/wait_time_model.py — Dynamic wait time prediction model.

Algorithm: GradientBoostingRegressor (scikit-learn)

WHY GRADIENT BOOSTING?
  - Handles non-linear relationships between features and wait time
  - Robust to outliers (students who show up very late don't distort model)
  - Works well on small-to-medium datasets (100–5000 training samples)
  - XGBoost would be marginally better, but sklearn GBR has zero extra deps

FEATURES:
  - current_active_orders: real-time queue depth at outlet (most important!)
  - hour_of_day: lunch rush vs off-peak
  - day_of_week: weekday vs weekend patterns
  - order_item_count: more items = longer prep
  - outlet_avg_prep_time: the outlet's historical baseline speed
  - is_peak_hour: binary flag (12-13, 18-19) for extra signal
  - order_source_is_platform: PLATFORM vs COUNTER orders may differ in speed

TARGET: actual_wait_minutes (order placed → ready_at)

OUTPUT: point estimate + 90% confidence interval
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MIN_TRAINING_ROWS = 30      # need at least 30 completed orders to train
DEFAULT_WAIT_MINUTES = 20   # safe fallback when model not ready


class WaitTimeModel:
    """
    Per-outlet or global wait time predictor.
    Scope: train one global model, use outlet_avg_prep_time as a feature
    so a single model handles all outlets.
    """

    def __init__(self):
        self.model: Optional[GradientBoostingRegressor] = None
        self.scaler: Optional[StandardScaler] = None
        self.is_fitted = False
        self.rmse = None
        self.feature_names = [
            "current_active_orders",
            "hour_of_day",
            "day_of_week",
            "order_item_count",
            "outlet_avg_prep_time",
            "is_peak_hour",
            "is_platform_order",
        ]

    def fit(self, df: pd.DataFrame) -> dict:
        """
        Train on historical completed orders.

        Args:
            df: DataFrame from get_wait_time_training_data() — must have
                actual_wait_minutes, order_item_count, hour_of_day,
                day_of_week, total_amount, order_source columns.

        Returns: dict with rmse and n_samples
        """
        if df.empty or len(df) < MIN_TRAINING_ROWS:
            logger.warning("[wait_time] Only %d rows — skipping training", len(df) if not df.empty else 0)
            return {"status": "insufficient_data", "n_samples": len(df) if not df.empty else 0}

        # Filter unreasonable wait times (< 2 min or > 90 min)
        df = df[
            (df["actual_wait_minutes"] >= 2) &
            (df["actual_wait_minutes"] <= 90)
        ].copy()

        if len(df) < MIN_TRAINING_ROWS:
            return {"status": "insufficient_data_after_filter", "n_samples": len(df)}

        # ── Feature engineering ───────────────────────────────────────────────
        df["is_peak_hour"] = df["hour_of_day"].apply(
            lambda h: 1 if h in [12, 13, 18, 19] else 0
        )
        df["is_platform_order"] = df["order_source"].apply(
            lambda s: 1 if s == "PLATFORM" else 0
        )
        # We don't have outlet_avg_prep_time in training data, use proxy from ready_at data
        # If missing, default to 20 minutes
        if "outlet_avg_prep_time" not in df.columns:
            df["outlet_avg_prep_time"] = 20.0
        # current_active_orders at time of order — approximate from hour
        # (real-time feature is only used at inference; use hour-of-day as proxy during training)
        if "current_active_orders" not in df.columns:
            df["current_active_orders"] = (df["hour_of_day"].apply(
                lambda h: 15 if h in [12, 13, 18, 19] else 5
            ))

        X = df[self.feature_names].values
        y = df["actual_wait_minutes"].values

        # ── Scale features ────────────────────────────────────────────────────
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # ── Train GBR ─────────────────────────────────────────────────────────
        # n_estimators=200: enough trees for accuracy without overfitting
        # max_depth=3: shallow trees → low variance (safer for small datasets)
        # learning_rate=0.05: slow learning → better generalisation
        # subsample=0.8: stochastic boosting reduces overfitting
        self.model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.8,
            loss="huber",       # robust to outlier wait times
            random_state=42,
        )
        self.model.fit(X_scaled, y)

        # Cross-validate RMSE (3-fold, safe for small datasets)
        cv_scores = cross_val_score(
            self.model, X_scaled, y,
            cv=min(3, len(df) // 10),
            scoring="neg_root_mean_squared_error",
        )
        self.rmse = round(float(-cv_scores.mean()), 2)
        self.is_fitted = True

        logger.info(
            "[wait_time] Trained | n=%d RMSE=%.2f min",
            len(df), self.rmse
        )
        return {"status": "trained", "n_samples": len(df), "rmse_minutes": self.rmse}

    def predict(
        self,
        outlet_id: int,
        order_item_count: int,
        current_active_orders: int,
        hour_of_day: int,
        day_of_week: int,
        outlet_avg_prep_time: float = 20.0,
        is_platform: bool = True,
    ) -> dict:
        """
        Predict wait time in minutes with a 90% confidence interval.

        Returns:
            {
                "estimatedMinutes": 18,
                "confidenceInterval": [14, 22],
                "strategy": "gradient_boosting" | "default_fallback"
            }
        """
        if not self.is_fitted or self.model is None:
            return self._default_response(outlet_avg_prep_time)

        try:
            is_peak = 1 if hour_of_day in [12, 13, 18, 19] else 0
            features = np.array([[
                current_active_orders,
                hour_of_day,
                day_of_week,
                order_item_count,
                outlet_avg_prep_time,
                is_peak,
                1 if is_platform else 0,
            ]])

            features_scaled = self.scaler.transform(features)
            point_estimate = float(self.model.predict(features_scaled)[0])
            point_estimate = max(2.0, min(90.0, point_estimate))

            # 90% CI: use RMSE as uncertainty proxy
            margin = max(3.0, (self.rmse or 5.0) * 1.645)
            low = max(1, round(point_estimate - margin))
            high = round(point_estimate + margin)

            return {
                "estimatedMinutes": round(point_estimate),
                "confidenceInterval": [low, high],
                "strategy": "gradient_boosting",
            }

        except Exception as exc:
            logger.warning("[wait_time] Prediction failed: %s", exc)
            return self._default_response(outlet_avg_prep_time)

    @staticmethod
    def _default_response(outlet_avg_prep_time: float) -> dict:
        base = max(5, round(outlet_avg_prep_time)) if outlet_avg_prep_time else DEFAULT_WAIT_MINUTES
        return {
            "estimatedMinutes": base,
            "confidenceInterval": [max(1, base - 5), base + 10],
            "strategy": "default_fallback",
        }