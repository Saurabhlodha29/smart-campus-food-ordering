"""
models/menu_analytics.py — Menu item performance analytics + combo suggestions.

Algorithm: Statistical analysis + Apriori-style association rule mining (mlxtend)
Falls back to frequency-based sorting if mlxtend is unavailable.

WHY ASSOCIATION RULES?
  - Apriori/FP-Growth finds items that are FREQUENTLY BOUGHT TOGETHER
  - This enables "Bundle X + Y at ₹90 (saves ₹10)" suggestions — exactly like Swiggy
  - Support + Confidence + Lift are standard e-commerce metrics recruiters recognise

ITEM PERFORMANCE METRICS:
  - order_frequency: what fraction of orders at this outlet include this item
  - revenue_contribution: this item's revenue / total outlet revenue
  - trend: RISING / STABLE / FALLING (compare last 7d vs previous 7d)
  - suggestion: actionable text for manager dashboard

COUNTER vs PLATFORM:
  Both are included in analytics — COUNTER orders represent real sales.
  The source is flagged in raw data so managers can see platform-only metrics.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

MIN_ORDERS_FOR_RULES = 10   # need at least 10 orders for meaningful rules
MIN_SUPPORT = 0.05          # item pair must appear in ≥5% of orders
MIN_CONFIDENCE = 0.3        # given item A, item B appears ≥30% of the time


class MenuAnalyticsModel:
    """
    Per-outlet menu analytics. Does not persist a trained model — recomputes
    on each request from recent data (fast enough for small outlet datasets).
    """

    def compute_performance(self, df: pd.DataFrame, all_items_df: pd.DataFrame) -> list[dict]:
        """
        Compute performance metrics for every item in an outlet's menu.

        Args:
            df:            order_items data from get_outlet_order_items()
            all_items_df:  all menu items for this outlet from get_menu_items()

        Returns: list of per-item performance dicts
        """
        if df.empty or all_items_df.empty:
            return []

        now = pd.Timestamp.now()
        df = df.copy()
        df["created_at"] = pd.to_datetime(df["created_at"])

        # ── Order frequency ───────────────────────────────────────────────────
        total_orders = df["order_id"].nunique()
        item_orders = df.groupby("menu_item_id")["order_id"].nunique()
        item_quantity = df.groupby("menu_item_id")["quantity"].sum()
        item_revenue = df.groupby("menu_item_id").apply(
            lambda g: (g["quantity"] * g["price_at_order"]).sum()
        )
        total_revenue = item_revenue.sum()

        # ── Trend: last 7d vs previous 7d ─────────────────────────────────────
        last_7 = df[df["created_at"] >= now - pd.Timedelta(days=7)]
        prev_7 = df[
            (df["created_at"] >= now - pd.Timedelta(days=14)) &
            (df["created_at"] < now - pd.Timedelta(days=7))
        ]
        last_7_qty = last_7.groupby("menu_item_id")["quantity"].sum()
        prev_7_qty = prev_7.groupby("menu_item_id")["quantity"].sum()

        result = []
        for _, item_row in all_items_df.iterrows():
            item_id = int(item_row["id"])
            n_orders = int(item_orders.get(item_id, 0))
            freq = round(n_orders / max(1, total_orders), 4)
            revenue = float(item_revenue.get(item_id, 0.0))
            rev_contribution = round(revenue / max(1, total_revenue), 4)

            # Trend
            l7 = int(last_7_qty.get(item_id, 0))
            p7 = int(prev_7_qty.get(item_id, 0))
            if p7 == 0 and l7 > 0:
                trend = "RISING"
            elif p7 > 0 and l7 >= p7 * 1.2:
                trend = "RISING"
            elif p7 > 0 and l7 <= p7 * 0.8:
                trend = "FALLING"
            else:
                trend = "STABLE"

            # Suggestion
            suggestion = self._generate_suggestion(freq, rev_contribution, trend, n_orders)

            result.append({
                "menuItemId": item_id,
                "itemName": item_row.get("name", ""),
                "orderFrequency": freq,
                "revenueContribution": rev_contribution,
                "totalOrders": n_orders,
                "trend": trend,
                "suggestion": suggestion,
            })

        # Sort by revenue contribution descending
        result.sort(key=lambda x: x["revenueContribution"], reverse=True)
        return result

    def compute_combos(self, df: pd.DataFrame, min_support: float = MIN_SUPPORT) -> list[dict]:
        """
        Find frequently ordered together item pairs using association rules.

        Args:
            df: order_items data from get_outlet_order_items()

        Returns: list of combo suggestions
        """
        if df.empty or df["order_id"].nunique() < MIN_ORDERS_FOR_RULES:
            return []

        # ── Build transaction matrix ───────────────────────────────────────────
        # Each row = one order, columns = items, value = 1 if ordered together
        basket = (
            df.groupby(["order_id", "menu_item_id"])["quantity"]
            .sum()
            .unstack(fill_value=0)
        )
        basket = (basket > 0).astype(int)

        n_orders = len(basket)
        item_cols = list(basket.columns)

        # ── Try mlxtend for proper Apriori ────────────────────────────────────
        try:
            from mlxtend.frequent_patterns import apriori, association_rules

            freq_items = apriori(
                basket,
                min_support=min_support,
                use_colnames=True,
                max_len=2,  # only pairs
            )
            if freq_items.empty:
                return self._simple_combo_fallback(df, n_orders)

            rules = association_rules(freq_items, metric="confidence", min_threshold=MIN_CONFIDENCE)
            rules = rules[rules["antecedents"].apply(len) == 1]
            rules = rules[rules["consequents"].apply(len) == 1]
            rules = rules.sort_values("lift", ascending=False).head(10)

            combos = []
            for _, rule in rules.iterrows():
                item_a_id = list(rule["antecedents"])[0]
                item_b_id = list(rule["consequents"])[0]
                combos.append({
                    "itemAId": int(item_a_id),
                    "itemBId": int(item_b_id),
                    "supportScore": round(float(rule["support"]), 3),
                    "confidence": round(float(rule["confidence"]), 3),
                    "lift": round(float(rule["lift"]), 3),
                    "suggestion": self._combo_suggestion(
                        df, item_a_id, item_b_id
                    ),
                })
            return combos

        except ImportError:
            logger.info("[menu_analytics] mlxtend not installed — using simple combo finder")
            return self._simple_combo_fallback(df, n_orders)

    def _simple_combo_fallback(self, df: pd.DataFrame, n_orders: int) -> list[dict]:
        """
        Simple co-occurrence matrix when mlxtend is unavailable.
        Counts how often item pairs appear in the same order.
        """
        from itertools import combinations

        order_items = df.groupby("order_id")["menu_item_id"].apply(list)
        pair_counts: dict[tuple, int] = {}

        for items in order_items:
            for pair in combinations(sorted(set(items)), 2):
                pair_counts[pair] = pair_counts.get(pair, 0) + 1

        if not pair_counts:
            return []

        combos = []
        for (a, b), count in sorted(pair_counts.items(), key=lambda x: -x[1])[:10]:
            support = round(count / n_orders, 3)
            if support < MIN_SUPPORT:
                continue
            combos.append({
                "itemAId": int(a),
                "itemBId": int(b),
                "supportScore": support,
                "confidence": None,  # not computed in simple fallback
                "lift": None,
                "suggestion": self._combo_suggestion(df, a, b),
            })
        return combos

    @staticmethod
    def _combo_suggestion(df: pd.DataFrame, item_a_id: int, item_b_id: int) -> str:
        """Generate a bundle deal suggestion for a pair of items."""
        try:
            price_a = df[df["menu_item_id"] == item_a_id]["price_at_order"].mean()
            price_b = df[df["menu_item_id"] == item_b_id]["price_at_order"].mean()
            combo_price = round((price_a + price_b) * 0.90)  # 10% discount
            savings = round(price_a + price_b - combo_price)
            return f"Bundle at ₹{combo_price} (saves ₹{savings})"
        except Exception:
            return "Consider bundling these items"

    @staticmethod
    def _generate_suggestion(freq: float, rev_contrib: float, trend: str, n_orders: int) -> str:
        """Generate an actionable suggestion for the manager dashboard."""
        if trend == "RISING" and freq > 0.3:
            return "Ensure stock is always available — rising demand"
        elif trend == "RISING":
            return "Consider featuring in outlet banner"
        elif freq > 0.5:
            return "Top seller — maintain quality"
        elif rev_contrib > 0.2:
            return "High revenue item — consider premium positioning"
        elif trend == "FALLING" and n_orders > 5:
            return "Declining popularity — consider a discount or recipe update"
        elif n_orders < 3:
            return "Low visibility — add a photo or feature in promotions"
        else:
            return "Performing normally"