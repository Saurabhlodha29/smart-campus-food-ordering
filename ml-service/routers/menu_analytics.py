"""
routers/menu_analytics.py — Menu item performance analytics + combo suggestions.

Endpoints:
    GET /analytics/menu-performance   → per-item stats for a manager
    GET /analytics/combos             → frequently ordered together items
    GET /analytics/outlet-summary     → aggregate outlet health metrics
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from database_connector import get_menu_items, get_outlet_order_items
from models.menu_analytics import MenuAnalyticsModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Menu Analytics"])

# MenuAnalyticsModel is stateless — recomputes from data on each call
_analytics = MenuAnalyticsModel()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ItemPerformance(BaseModel):
    menuItemId: int
    itemName: str
    orderFrequency: float       # fraction of orders including this item
    revenueContribution: float  # fraction of outlet's total revenue
    totalOrders: int
    trend: str                  # RISING | STABLE | FALLING
    suggestion: str             # actionable text for manager


class MenuPerformanceResponse(BaseModel):
    outletId: int
    items: list[ItemPerformance]
    analysisDays: int


class ComboItem(BaseModel):
    itemAId: int
    itemBId: int
    supportScore: float
    confidence: Optional[float]
    lift: Optional[float]
    suggestion: str


class CombosResponse(BaseModel):
    outletId: int
    combos: list[ComboItem]
    analysisDays: int


class OutletSummary(BaseModel):
    outletId: int
    totalOrders: int
    totalRevenue: float
    platformOrders: int
    counterOrders: int
    uniqueItems: int
    topItem: Optional[str]
    analysisDays: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/menu-performance", response_model=MenuPerformanceResponse)
def get_menu_performance(outletId: int, days: int = 30) -> MenuPerformanceResponse:
    """
    ML-powered menu performance analytics for outlet managers.

    Returns per-item metrics with actionable suggestions:
    - Which items are rising/falling in popularity
    - Revenue contribution per item
    - Suggestions like "feature in banner" or "consider discount"

    Both PLATFORM and COUNTER orders are included in analysis —
    they both represent real sales. Managers see total demand.

    Returns empty items list gracefully if no data.
    """
    try:
        order_df = get_outlet_order_items(outletId, days=days)
        menu_df = get_menu_items(outlet_id=outletId)

        if order_df.empty or menu_df.empty:
            return MenuPerformanceResponse(
                outletId=outletId,
                items=[],
                analysisDays=days,
            )

        items = _analytics.compute_performance(order_df, menu_df)
        return MenuPerformanceResponse(
            outletId=outletId,
            items=[ItemPerformance(**item) for item in items],
            analysisDays=days,
        )
    except Exception as exc:
        logger.error("[menu_analytics] Performance error for outlet %s: %s", outletId, exc)
        return MenuPerformanceResponse(outletId=outletId, items=[], analysisDays=days)


@router.get("/combos", response_model=CombosResponse)
def get_combos(outletId: int, days: int = 30) -> CombosResponse:
    """
    Find items that are frequently ordered together at this outlet.

    Used to create bundle deals like:
      "Veg Burger + Cold Coffee — Bundle at ₹90 (saves ₹10)"

    Powered by association rule mining (Apriori/FP-Growth).
    Falls back to simple co-occurrence counting if mlxtend unavailable.

    Returns empty combos list gracefully if not enough data.
    """
    try:
        order_df = get_outlet_order_items(outletId, days=days)
        if order_df.empty:
            return CombosResponse(outletId=outletId, combos=[], analysisDays=days)

        combos = _analytics.compute_combos(order_df)
        return CombosResponse(
            outletId=outletId,
            combos=[ComboItem(**c) for c in combos],
            analysisDays=days,
        )
    except Exception as exc:
        logger.error("[menu_analytics] Combos error for outlet %s: %s", outletId, exc)
        return CombosResponse(outletId=outletId, combos=[], analysisDays=days)


@router.get("/outlet-summary", response_model=OutletSummary)
def get_outlet_summary(outletId: int, days: int = 30) -> OutletSummary:
    """
    High-level health summary for an outlet.
    Shows platform vs counter split so managers understand their channel mix.
    """
    try:
        order_df = get_outlet_order_items(outletId, days=days)

        if order_df.empty:
            return OutletSummary(
                outletId=outletId,
                totalOrders=0, totalRevenue=0.0,
                platformOrders=0, counterOrders=0,
                uniqueItems=0, topItem=None,
                analysisDays=days,
            )

        import pandas as pd
        total_orders = order_df["order_id"].nunique()
        total_revenue = float((order_df["quantity"] * order_df["price_at_order"]).sum())
        platform_orders = order_df[order_df["order_source"] == "PLATFORM"]["order_id"].nunique()
        counter_orders = order_df[order_df["order_source"] == "COUNTER"]["order_id"].nunique()
        unique_items = order_df["menu_item_id"].nunique()

        # Top item by quantity
        top = (
            order_df.groupby("item_name")["quantity"]
            .sum()
            .idxmax()
        ) if not order_df.empty else None

        return OutletSummary(
            outletId=outletId,
            totalOrders=total_orders,
            totalRevenue=round(total_revenue, 2),
            platformOrders=platform_orders,
            counterOrders=counter_orders,
            uniqueItems=unique_items,
            topItem=top,
            analysisDays=days,
        )
    except Exception as exc:
        logger.error("[outlet_summary] Error for outlet %s: %s", outletId, exc)
        return OutletSummary(
            outletId=outletId, totalOrders=0, totalRevenue=0.0,
            platformOrders=0, counterOrders=0, uniqueItems=0,
            topItem=None, analysisDays=days,
        )