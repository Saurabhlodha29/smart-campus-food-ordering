"""
routers/recommendations.py — Personalised food recommendation endpoints.

Endpoints:
    POST /recommend/food        → personalised recommendations for a user at an outlet
    GET  /recommend/trending    → trending items at an outlet in the last 7 days
    POST /recommend/retrain     → manually trigger recommender retraining
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database_connector import (
    get_menu_items,
    get_order_history,
    get_trending_items,
    get_user_order_matrix,
    _query_to_df,
)
from model_registry import registry
from models.hybrid_recommender import HybridRecommender

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommend", tags=["Recommendations"])

MODEL_NAME = "recommender"


# ── Schemas ───────────────────────────────────────────────────────────────────

class FoodRecommendRequest(BaseModel):
    userId: int = Field(..., gt=0, example=5)
    outletId: int = Field(..., gt=0, example=2)
    campusId: int = Field(..., gt=0, example=1)
    limit: int = Field(default=5, ge=1, le=20)


class RecommendedItem(BaseModel):
    menuItemId: int
    score: float
    reason: str


class FoodRecommendResponse(BaseModel):
    recommendations: list[RecommendedItem]
    strategy: str       # "hybrid" | "popularity_fallback" | "cold_start"
    userId: int
    outletId: int


class TrendingItem(BaseModel):
    menuItemId: int
    itemName: str
    totalOrdered: int
    orderFrequency: int


class RetrainResponse(BaseModel):
    status: str
    campusId: Optional[int]
    metrics: dict


# ── Training function (called on startup + by scheduler) ─────────────────────

def train_recommender(campus_id: int) -> dict:
    """Train or retrain the hybrid recommender for a specific campus."""
    logger.info("[recommender] Training for campus_id=%s", campus_id)

    user_item_matrix = get_user_order_matrix(campus_id)
    order_history = get_order_history(campus_id=campus_id, days=90)
    menu_items = get_menu_items()  # all items across campus

    if user_item_matrix.empty or menu_items.empty:
        logger.warning("[recommender campus=%s] No data — skipping", campus_id)
        return {"status": "no_data"}

    menu_items_for_fit = menu_items.rename(columns={"id": "id"})

    recommender = HybridRecommender(campus_id=campus_id)
    metrics = recommender.fit(user_item_matrix, menu_items_for_fit, order_history)

    registry.save(MODEL_NAME, recommender, scope_id=campus_id, metrics=metrics)
    logger.info("[recommender campus=%s] Training complete: %s", campus_id, metrics)
    return metrics


def train_all_campuses() -> None:
    """Train recommender for all campuses with data. Called by APScheduler."""
    sql = "SELECT DISTINCT campus_id FROM outlets WHERE status = 'ACTIVE'"
    df = _query_to_df(sql)
    if df.empty:
        logger.info("[recommender] No active campuses found")
        return
    for cid in df["campus_id"].tolist():
        try:
            train_recommender(int(cid))
        except Exception as exc:
            logger.error("[recommender] Training failed for campus %s: %s", cid, exc)


# ── Helper: get user's order count ────────────────────────────────────────────

def _get_user_order_count(user_id: int) -> int:
    sql = """
        SELECT COUNT(*) AS cnt FROM orders
        WHERE student_id = %(user_id)s AND status != 'CANCELLED'
    """
    df = _query_to_df(sql, {"user_id": user_id})
    if df.empty:
        return 0
    return int(df.iloc[0]["cnt"])


def _get_outlet_item_ids(outlet_id: int) -> list[int]:
    """Return IDs of all available items at an outlet."""
    sql = """
        SELECT id FROM menu_items
        WHERE outlet_id = %(outlet_id)s AND is_available = true
    """
    df = _query_to_df(sql, {"outlet_id": outlet_id})
    if df.empty:
        return []
    return df["id"].tolist()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/food", response_model=FoodRecommendResponse)
def get_food_recommendations(req: FoodRecommendRequest) -> FoodRecommendResponse:
    """
    Get personalised food recommendations for a student at a specific outlet.

    Called when a student opens an outlet's menu page in the app.
    Returns a "Recommended for You" section with up to `limit` items.

    Cold start behaviour:
    - User has < 3 orders → returns popularity-based recommendations
    - Model not trained yet → returns popularity-based recommendations
    - Outlet has no items → returns empty list (no 500 error)
    """
    outlet_item_ids = _get_outlet_item_ids(req.outletId)

    if not outlet_item_ids:
        return FoodRecommendResponse(
            recommendations=[],
            strategy="no_items",
            userId=req.userId,
            outletId=req.outletId,
        )

    user_order_count = _get_user_order_count(req.userId)
    recommender: HybridRecommender = registry.load(MODEL_NAME, scope_id=req.campusId)

    # ── Cold start or model not trained ────────────────────────────────────
    if recommender is None or user_order_count < 3:
        trending = get_trending_items(req.outletId, req.campusId, days=7, limit=req.limit)
        items = [
            RecommendedItem(
                menuItemId=int(t["menu_item_id"]),
                score=round(float(t.get("total_ordered", 1)) / max(1, sum(x.get("total_ordered", 1) for x in trending)), 4),
                reason="Popular at this outlet"
            )
            for t in trending[:req.limit]
        ]
        # Pad with outlet items if not enough trending
        if len(items) < req.limit:
            seen = {i.menuItemId for i in items}
            for iid in outlet_item_ids:
                if iid not in seen:
                    items.append(RecommendedItem(menuItemId=iid, score=0.1, reason="Try this"))
                if len(items) >= req.limit:
                    break
        return FoodRecommendResponse(
            recommendations=items,
            strategy="cold_start_popularity",
            userId=req.userId,
            outletId=req.outletId,
        )

    # ── Personalised hybrid recommendations ────────────────────────────────
    try:
        raw = recommender.recommend(
            user_id=req.userId,
            outlet_id=req.outletId,
            outlet_item_ids=outlet_item_ids,
            user_order_count=user_order_count,
            limit=req.limit,
        )
        items = [
            RecommendedItem(
                menuItemId=r["menuItemId"],
                score=r["score"],
                reason=r["reason"],
            )
            for r in raw
        ]
        return FoodRecommendResponse(
            recommendations=items,
            strategy="hybrid",
            userId=req.userId,
            outletId=req.outletId,
        )
    except Exception as exc:
        logger.error("[recommend/food] Error for user=%s: %s", req.userId, exc)
        # Never return 500 — fall back to popularity
        trending = get_trending_items(req.outletId, req.campusId, days=7, limit=req.limit)
        items = [
            RecommendedItem(menuItemId=int(t["menu_item_id"]), score=0.5, reason="Popular at this outlet")
            for t in trending
        ]
        return FoodRecommendResponse(
            recommendations=items,
            strategy="error_fallback",
            userId=req.userId,
            outletId=req.outletId,
        )


@router.get("/trending")
def get_trending(
    outletId: int,
    campusId: int,
    limit: int = 10,
) -> list[dict]:
    """
    Get trending items at an outlet in the past 7 days.

    Useful for the outlet homepage banner and "What's hot" section.
    Returns empty list gracefully if no data.
    """
    try:
        items = get_trending_items(outletId, campusId, days=7, limit=limit)
        return [
            {
                "menuItemId": int(t["menu_item_id"]),
                "itemName": t.get("name", ""),
                "totalOrdered": int(t.get("total_ordered", 0)),
                "orderFrequency": int(t.get("order_frequency", 0)),
            }
            for t in items
        ]
    except Exception as exc:
        logger.error("[recommend/trending] Error: %s", exc)
        return []


@router.post("/retrain", response_model=RetrainResponse)
def retrain_recommender(campus_id: Optional[int] = None) -> RetrainResponse:
    """
    Manually trigger recommender retraining.
    Pass campus_id to retrain for a specific campus, or omit to retrain all.
    """
    try:
        if campus_id:
            metrics = train_recommender(campus_id)
            return RetrainResponse(status="retrained", campusId=campus_id, metrics=metrics)
        else:
            train_all_campuses()
            return RetrainResponse(status="retrained_all", campusId=None, metrics={})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retraining failed: {exc}")