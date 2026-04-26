"""
routers/slot_forecast.py — Pickup slot demand forecasting endpoints.

Endpoints:
    GET /forecast/slot-demand   → predicted order count per hour for a date
    GET /forecast/peak-hours    → which hours are peak vs low for an outlet
    POST /forecast/retrain      → retrain forecast model for an outlet
"""

import logging
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database_connector import get_outlet_load_series
from model_registry import registry
from models.demand_forecast import DemandForecastModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/forecast", tags=["Slot Demand Forecast"])

MODEL_PREFIX = "forecast"


# ── Schemas ───────────────────────────────────────────────────────────────────

class SlotDemandEntry(BaseModel):
    hour: int
    predictedOrders: int
    suggestedSlotCapacity: int


class SlotDemandResponse(BaseModel):
    outletId: int
    date: str
    hourlyForecast: list[SlotDemandEntry]
    strategy: str


class PeakHoursResponse(BaseModel):
    outletId: int
    peakHours: list[int]
    lowHours: list[int]


class RetrainResponse(BaseModel):
    status: str
    outletId: int
    metrics: dict


# ── Training function ─────────────────────────────────────────────────────────

def train_forecast_model(outlet_id: int) -> dict:
    """Train or retrain the demand forecast model for a specific outlet."""
    logger.info("[forecast] Training for outlet_id=%s", outlet_id)
    series_df = get_outlet_load_series(outlet_id, days=90)

    model = DemandForecastModel(outlet_id=outlet_id)
    metrics = model.fit(series_df)

    if model.is_fitted:
        registry.save(MODEL_PREFIX, model, scope_id=outlet_id, metrics=metrics)
        logger.info("[forecast outlet=%s] Training done: %s", outlet_id, metrics)

    return metrics


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/slot-demand", response_model=SlotDemandResponse)
def get_slot_demand(outletId: int, date: date = None) -> SlotDemandResponse:
    """
    Predict order volume per hour for a specific date at an outlet.

    Used by the manager dashboard to decide:
      - How many orders to accept per pickup slot
      - When to open/close slots proactively

    Returns 24 hourly entries. If model is not trained, returns all zeros
    with suggested capacity of 5 (safe default for any slot).
    """
    if date is None:
        from datetime import date as date_cls
        date = date_cls.today()

    date_str = date.isoformat()

    model: DemandForecastModel = registry.load(MODEL_PREFIX, scope_id=outletId)

    # ── Cold start: train on first request ────────────────────────────────
    if model is None:
        try:
            train_forecast_model(outletId)
            model = registry.load(MODEL_PREFIX, scope_id=outletId)
        except Exception as exc:
            logger.warning("[forecast] On-demand training failed for outlet %s: %s", outletId, exc)

    if model is None:
        # Return empty forecast with safe defaults
        return SlotDemandResponse(
            outletId=outletId,
            date=date_str,
            hourlyForecast=[
                SlotDemandEntry(hour=h, predictedOrders=0, suggestedSlotCapacity=5)
                for h in range(24)
            ],
            strategy="no_data_defaults",
        )

    try:
        hourly = model.forecast_day(date)
        return SlotDemandResponse(
            outletId=outletId,
            date=date_str,
            hourlyForecast=[
                SlotDemandEntry(
                    hour=e["hour"],
                    predictedOrders=e["predictedOrders"],
                    suggestedSlotCapacity=e["suggestedSlotCapacity"],
                )
                for e in hourly
            ],
            strategy=model.strategy_used,
        )
    except Exception as exc:
        logger.error("[forecast] Prediction failed for outlet %s: %s", outletId, exc)
        return SlotDemandResponse(
            outletId=outletId,
            date=date_str,
            hourlyForecast=[
                SlotDemandEntry(hour=h, predictedOrders=0, suggestedSlotCapacity=5)
                for h in range(24)
            ],
            strategy="error_fallback",
        )


@router.get("/peak-hours", response_model=PeakHoursResponse)
def get_peak_hours(outletId: int) -> PeakHoursResponse:
    """
    Return historically peak and low-traffic hours for an outlet.

    Used by the manager dashboard to:
      - Highlight when to have extra staff
      - Suggest when to run promotions (low hours)
      - Set default slot capacities
    """
    model: DemandForecastModel = registry.load(MODEL_PREFIX, scope_id=outletId)

    if model is None:
        # Return sensible campus defaults
        return PeakHoursResponse(
            outletId=outletId,
            peakHours=[12, 13, 18, 19],
            lowHours=[9, 10, 15, 16],
        )

    try:
        result = model.get_peak_hours()
        return PeakHoursResponse(
            outletId=outletId,
            peakHours=result["peakHours"],
            lowHours=result["lowHours"],
        )
    except Exception as exc:
        logger.error("[forecast/peak-hours] Error for outlet %s: %s", outletId, exc)
        return PeakHoursResponse(
            outletId=outletId,
            peakHours=[12, 13, 18, 19],
            lowHours=[9, 10, 15, 16],
        )


@router.post("/retrain", response_model=RetrainResponse)
def retrain_forecast(outletId: int) -> RetrainResponse:
    """Manually retrain the demand forecast model for a specific outlet."""
    try:
        metrics = train_forecast_model(outletId)
        return RetrainResponse(
            status=metrics.get("status", "unknown"),
            outletId=outletId,
            metrics=metrics,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retraining failed: {exc}")