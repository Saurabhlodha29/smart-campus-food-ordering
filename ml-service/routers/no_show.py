"""
routers/no_show.py — No-show / order abandonment risk prediction endpoints.

This EXTENDS (does not replace) the existing demand-score prediction.
The existing POST /predict/demand-score is in main.py — untouched.

Endpoints:
    POST /predict/no-show-risk  → predict no-show probability for a user+order
    POST /predict/no-show-risk/retrain → retrain the classifier
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database_connector import get_no_show_training_data, get_user_stats
from model_registry import registry
from models.no_show_classifier import NoShowClassifier

logger = logging.getLogger(__name__)
router = APIRouter(tags=["No-Show Risk"])

MODEL_NAME = "no_show"


# ── Schemas ───────────────────────────────────────────────────────────────────

class NoShowRiskRequest(BaseModel):
    userId: int = Field(..., gt=0, example=5)
    orderAmount: float = Field(..., gt=0, example=120.0)
    slotHour: int = Field(..., ge=0, le=23, example=13)
    minutesUntilSlot: int = Field(default=30, ge=0, example=45)


class NoShowRiskResponse(BaseModel):
    noShowProbability: float
    riskLevel: str          # HIGH | MEDIUM | LOW
    recommendation: str
    strategy: str
    userId: int


class RetrainResponse(BaseModel):
    status: str
    metrics: dict


# ── Training function ─────────────────────────────────────────────────────────

def train_no_show_model() -> dict:
    """Train or retrain the global no-show classifier."""
    logger.info("[no_show] Training global classifier…")
    df = get_no_show_training_data(days=90)

    model = NoShowClassifier()
    metrics = model.fit(df)

    if metrics.get("status") == "trained":
        registry.save(MODEL_NAME, model, scope_id=0, metrics=metrics)
        logger.info("[no_show] Training complete: %s", metrics)
    else:
        logger.warning("[no_show] Training skipped: %s", metrics)

    return metrics


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/predict/no-show-risk", response_model=NoShowRiskResponse)
def predict_no_show_risk(req: NoShowRiskRequest) -> NoShowRiskResponse:
    """
    Predict the probability that a user will not pick up their order.

    Called by PenaltyService or OrderService just after an order is placed.
    The result feeds into:
      - Advance payment lock decisions (HIGH risk → require online payment)
      - Manager alert dashboard (show high-risk orders in a different colour)
      - Pickup reminder timing

    COUNTER orders (walk-in customers) do not go through this endpoint —
    they have no registered user and no no-show risk.

    Cold start: users with 0 orders get a neutral 0.3 probability.
    Never returns a 500 error.
    """
    # ── Fetch user behaviour stats from DB ────────────────────────────────
    try:
        stats = get_user_stats(req.userId)
    except Exception as exc:
        logger.warning("[no_show] Could not fetch user stats for %s: %s", req.userId, exc)
        stats = {
            "no_show_rate": 0.1,
            "total_orders": 0,
            "cancel_rate": 0.0,
            "avg_order_amount": req.orderAmount,
            "orders_last_7d": 0,
        }

    # ── Load model ────────────────────────────────────────────────────────
    model: NoShowClassifier = registry.load(MODEL_NAME, scope_id=0)

    if model is None:
        # Rule-based fallback using only historical no-show rate
        prob = NoShowClassifier._rule_based_score(
            no_show_rate=stats["no_show_rate"],
            slot_hour=req.slotHour,
            order_amount=req.orderAmount,
        )
        risk_level = "HIGH" if prob >= 0.65 else ("MEDIUM" if prob >= 0.35 else "LOW")
        recommendation = (
            "Consider advance payment lock" if risk_level == "HIGH"
            else "Send pickup reminder" if risk_level == "MEDIUM"
            else "No action needed"
        )
        return NoShowRiskResponse(
            noShowProbability=round(prob, 4),
            riskLevel=risk_level,
            recommendation=recommendation,
            strategy="rule_based_no_model",
            userId=req.userId,
        )

    # ── ML prediction ─────────────────────────────────────────────────────
    try:
        result = model.predict(
            no_show_rate=stats["no_show_rate"],
            total_orders=stats["total_orders"],
            order_amount=req.orderAmount,
            slot_hour=req.slotHour,
            orders_last_7d=stats["orders_last_7d"],
            cancel_rate=stats.get("cancel_rate", 0.0),
        )
        return NoShowRiskResponse(
            noShowProbability=result["noShowProbability"],
            riskLevel=result["riskLevel"],
            recommendation=result["recommendation"],
            strategy=result["strategy"],
            userId=req.userId,
        )
    except Exception as exc:
        logger.error("[no_show] Prediction error for user %s: %s", req.userId, exc)
        return NoShowRiskResponse(
            noShowProbability=0.3,
            riskLevel="LOW",
            recommendation="Prediction unavailable — treating as low risk",
            strategy="error_fallback",
            userId=req.userId,
        )


@router.post("/predict/no-show-risk/retrain", response_model=RetrainResponse)
def retrain_no_show() -> RetrainResponse:
    """Manually trigger no-show classifier retraining."""
    try:
        metrics = train_no_show_model()
        return RetrainResponse(status=metrics.get("status", "unknown"), metrics=metrics)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retraining failed: {exc}")