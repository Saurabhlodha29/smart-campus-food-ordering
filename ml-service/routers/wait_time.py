"""
routers/wait_time.py — Dynamic estimated wait time prediction endpoints.

Endpoints:
    POST /predict/wait-time   → predict wait time for an order being placed
    POST /predict/wait-time/retrain → manually retrain the wait time model
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database_connector import (
    get_active_order_count,
    get_outlet_avg_prep_time,
    get_wait_time_training_data,
)
from model_registry import registry
from models.wait_time_model import WaitTimeModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Wait Time"])

MODEL_NAME = "wait_time"


# ── Schemas ───────────────────────────────────────────────────────────────────

class WaitTimeRequest(BaseModel):
    outletId: int = Field(..., gt=0, example=2)
    orderItemCount: int = Field(..., ge=1, le=50, example=3)
    currentActiveOrders: int = Field(
        default=-1,
        description="Pass -1 to let the service fetch live count from DB",
        example=12,
    )
    hourOfDay: int = Field(
        default=-1,
        description="0–23. Pass -1 to use current server time.",
        example=13,
    )
    dayOfWeek: int = Field(
        default=-1,
        description="0=Mon…6=Sun. Pass -1 to use current server time.",
        example=2,
    )


class WaitTimeResponse(BaseModel):
    estimatedMinutes: int
    confidenceInterval: list[int]   # [low, high]
    strategy: str
    outletId: int


class RetrainResponse(BaseModel):
    status: str
    metrics: dict


# ── Training function ─────────────────────────────────────────────────────────

def train_wait_time_model() -> dict:
    """Train or retrain the global wait time model. Called on startup + by scheduler."""
    logger.info("[wait_time] Training global model…")
    df = get_wait_time_training_data(days=60)

    model = WaitTimeModel()
    metrics = model.fit(df)

    if metrics.get("status") == "trained":
        registry.save(MODEL_NAME, model, scope_id=0, metrics=metrics)
        logger.info("[wait_time] Training complete: %s", metrics)
    else:
        logger.warning("[wait_time] Training skipped: %s", metrics)

    return metrics


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/predict/wait-time", response_model=WaitTimeResponse)
def predict_wait_time(req: WaitTimeRequest) -> WaitTimeResponse:
    """
    Predict the estimated wait time for an order at the point of placement.

    Called by the Spring Boot OrderService just before creating an order,
    so the student sees a real predicted time instead of a fixed "30 mins".

    If currentActiveOrders is -1, we query the DB live for the most accurate
    real-time queue depth. If hourOfDay / dayOfWeek are -1, we use the
    current server time.

    Never returns a 500 error — falls back to outlet's historical avg prep time.
    """
    now = datetime.now()

    # ── Resolve real-time values if not provided ──────────────────────────
    hour = req.hourOfDay if req.hourOfDay >= 0 else now.hour
    dow = req.dayOfWeek if req.dayOfWeek >= 0 else now.weekday()

    if req.currentActiveOrders < 0:
        try:
            active_orders = get_active_order_count(req.outletId)
        except Exception:
            active_orders = 5   # safe default
    else:
        active_orders = req.currentActiveOrders

    # ── Outlet's historical average prep time ─────────────────────────────
    try:
        outlet_avg = get_outlet_avg_prep_time(req.outletId)
    except Exception:
        outlet_avg = 20.0

    # ── Load model and predict ────────────────────────────────────────────
    model: WaitTimeModel = registry.load(MODEL_NAME, scope_id=0)

    if model is None:
        # Model not trained yet — use outlet average
        base = round(outlet_avg)
        return WaitTimeResponse(
            estimatedMinutes=base,
            confidenceInterval=[max(1, base - 5), base + 10],
            strategy="outlet_avg_fallback",
            outletId=req.outletId,
        )

    result = model.predict(
        outlet_id=req.outletId,
        order_item_count=req.orderItemCount,
        current_active_orders=active_orders,
        hour_of_day=hour,
        day_of_week=dow,
        outlet_avg_prep_time=outlet_avg,
        is_platform=True,
    )

    return WaitTimeResponse(
        estimatedMinutes=result["estimatedMinutes"],
        confidenceInterval=result["confidenceInterval"],
        strategy=result["strategy"],
        outletId=req.outletId,
    )


@router.post("/predict/wait-time/retrain", response_model=RetrainResponse)
def retrain_wait_time() -> RetrainResponse:
    """Manually trigger wait time model retraining."""
    try:
        metrics = train_wait_time_model()
        return RetrainResponse(status=metrics.get("status", "unknown"), metrics=metrics)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retraining failed: {exc}")