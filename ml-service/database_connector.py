"""
database_connector.py — Central data access layer for all ML features.

Connects to the same Supabase PostgreSQL that Spring Boot uses.
All credentials come from the same environment variables as database.py.

This module ADDS to the existing database.py — it does NOT replace it.
Import this module in the new routers; import database.py in the old ones.

Key functions:
  get_order_history()        → DataFrame of orders for training
  get_menu_items()           → DataFrame of menu items for content-based filtering
  get_user_order_matrix()    → Pivot table (user × item) for collaborative filtering
  get_outlet_load_series()   → Time-series of orders per hour for forecasting
  get_active_order_count()   → Real-time count of orders being prepared
  get_user_stats()           → Per-user behaviour stats for no-show prediction
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Reuse the same DB config as database.py ────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME",     "campus_food_dev"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "Project@291231"),
}


@contextmanager
def _get_conn():
    """Context-managed connection — always closed on exit."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


def _query_to_df(sql: str, params: dict = None) -> pd.DataFrame:
    """Execute a query and return results as a DataFrame. Returns empty DataFrame on error."""
    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params or {})
                rows = cur.fetchall()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])
    except Exception as exc:
        logger.error("DB query failed: %s", exc)
        return pd.DataFrame()


# ── Feature 1 & 5: Order history ───────────────────────────────────────────────

def get_order_history(campus_id: Optional[int] = None, days: int = 90) -> pd.DataFrame:
    """
    Returns order + order_item data for the past `days` days.

    Columns: order_id, user_id, outlet_id, campus_id, menu_item_id, quantity,
             price_at_order, category, item_name, item_price, created_at,
             status, total_amount, order_source

    order_source is included so ML can distinguish PLATFORM vs COUNTER orders.
    COUNTER orders are kept in training data — they represent real demand signals —
    but flagged so you can analyze platform-only patterns separately.
    """
    campus_filter = "AND u.campus_id = %(campus_id)s" if campus_id else ""
    sql = f"""
        SELECT
            o.id                 AS order_id,
            o.student_id         AS user_id,
            o.outlet_id,
            out.campus_id,
            oi.menu_item_id,
            oi.quantity,
            oi.price_at_order,
            mi.name              AS item_name,
            mi.price             AS item_price,
            mi.prep_time         AS prep_time,
            o.created_at,
            o.status,
            o.total_amount,
            COALESCE(o.order_source, 'PLATFORM') AS order_source
        FROM order_items oi
        JOIN orders      o   ON oi.order_id     = o.id
        JOIN menu_items  mi  ON oi.menu_item_id = mi.id
        JOIN outlets     out ON o.outlet_id      = out.id
        LEFT JOIN users  u   ON o.student_id     = u.id
        WHERE o.created_at >= NOW() - INTERVAL '%(days)s days'
          AND o.status != 'CANCELLED'
          {campus_filter}
        ORDER BY o.created_at DESC
    """
    params = {"days": days, "campus_id": campus_id}
    return _query_to_df(sql, params)


def get_menu_items(outlet_id: Optional[int] = None) -> pd.DataFrame:
    """
    Returns menu item metadata for content-based filtering.

    Columns: id, outlet_id, campus_id, name, price, prep_time, is_available
    """
    outlet_filter = "WHERE mi.outlet_id = %(outlet_id)s" if outlet_id else ""
    sql = f"""
        SELECT
            mi.id,
            mi.outlet_id,
            out.campus_id,
            mi.name,
            mi.price,
            mi.prep_time,
            mi.is_available
        FROM menu_items mi
        JOIN outlets out ON mi.outlet_id = out.id
        {outlet_filter}
        ORDER BY mi.id
    """
    params = {"outlet_id": outlet_id} if outlet_id else {}
    return _query_to_df(sql, params)


def get_user_order_matrix(campus_id: int) -> pd.DataFrame:
    """
    Returns a user × menu_item interaction matrix for collaborative filtering.

    Each cell = total quantity of that item ordered by that user.
    Only includes PLATFORM orders (COUNTER orders have no real user_id).

    Returns a pivot table: rows = user_id, columns = menu_item_id, values = quantity.
    """
    sql = """
        SELECT
            o.student_id         AS user_id,
            oi.menu_item_id,
            SUM(oi.quantity)     AS total_quantity
        FROM order_items oi
        JOIN orders      o   ON oi.order_id     = o.id
        JOIN outlets     out ON o.outlet_id      = out.id
        WHERE out.campus_id = %(campus_id)s
          AND o.status != 'CANCELLED'
          AND o.student_id IS NOT NULL
          AND COALESCE(o.order_source, 'PLATFORM') = 'PLATFORM'
          AND o.created_at >= NOW() - INTERVAL '90 days'
        GROUP BY o.student_id, oi.menu_item_id
    """
    df = _query_to_df(sql, {"campus_id": campus_id})
    if df.empty:
        return pd.DataFrame()
    pivot = df.pivot_table(
        index="user_id", columns="menu_item_id",
        values="total_quantity", fill_value=0
    )
    return pivot


# ── Feature 2: Wait time training data ─────────────────────────────────────────

def get_wait_time_training_data(outlet_id: Optional[int] = None, days: int = 60) -> pd.DataFrame:
    """
    Returns completed orders with actual wait times (placed → ready).

    Only orders that reached PICKED or READY status have meaningful wait times.
    Columns: outlet_id, order_item_count, hour_of_day, day_of_week,
             total_amount, order_source, actual_wait_minutes
    """
    outlet_filter = "AND o.outlet_id = %(outlet_id)s" if outlet_id else ""
    sql = f"""
        SELECT
            o.outlet_id,
            COUNT(oi.id)                                              AS order_item_count,
            EXTRACT(HOUR FROM o.created_at)::int                      AS hour_of_day,
            EXTRACT(DOW  FROM o.created_at)::int                      AS day_of_week,
            o.total_amount,
            COALESCE(o.order_source, 'PLATFORM')                     AS order_source,
            GREATEST(0,
                EXTRACT(EPOCH FROM (o.ready_at - o.created_at)) / 60
            )::float                                                  AS actual_wait_minutes
        FROM orders     o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status IN ('PICKED', 'READY', 'EXPIRED')
          AND o.ready_at IS NOT NULL
          AND o.ready_at > o.created_at
          AND o.created_at >= NOW() - INTERVAL '%(days)s days'
          {outlet_filter}
        GROUP BY o.id, o.outlet_id, o.created_at, o.ready_at,
                 o.total_amount, o.order_source
        HAVING EXTRACT(EPOCH FROM (o.ready_at - o.created_at)) / 60 < 120
    """
    params = {"days": days, "outlet_id": outlet_id}
    return _query_to_df(sql, params)


def get_active_order_count(outlet_id: int) -> int:
    """Returns real-time count of PLACED + PREPARING orders at an outlet."""
    sql = """
        SELECT COUNT(*) AS cnt
        FROM orders
        WHERE outlet_id = %(outlet_id)s
          AND status IN ('PLACED', 'PREPARING')
    """
    df = _query_to_df(sql, {"outlet_id": outlet_id})
    if df.empty:
        return 0
    return int(df.iloc[0]["cnt"])


def get_outlet_avg_prep_time(outlet_id: int) -> float:
    """Returns avg prep time in minutes for an outlet from historical data."""
    sql = """
        SELECT AVG(EXTRACT(EPOCH FROM (ready_at - created_at)) / 60) AS avg_mins
        FROM orders
        WHERE outlet_id = %(outlet_id)s
          AND status IN ('PICKED', 'READY')
          AND ready_at IS NOT NULL
          AND ready_at > created_at
          AND created_at >= NOW() - INTERVAL '30 days'
    """
    df = _query_to_df(sql, {"outlet_id": outlet_id})
    if df.empty or df.iloc[0]["avg_mins"] is None:
        return 20.0  # safe default
    return float(df.iloc[0]["avg_mins"])


# ── Feature 3: Slot demand forecasting ─────────────────────────────────────────

def get_outlet_load_series(outlet_id: int, days: int = 90) -> pd.DataFrame:
    """
    Returns hourly order counts for an outlet over the past `days` days.
    Used for Prophet/SARIMA time-series forecasting.

    Columns: ds (datetime), y (order_count), hour_of_day, day_of_week
    Both PLATFORM and COUNTER orders are included (both represent real load).
    """
    sql = """
        SELECT
            DATE_TRUNC('hour', o.created_at)   AS ds,
            COUNT(*)                            AS y,
            EXTRACT(HOUR FROM o.created_at)::int AS hour_of_day,
            EXTRACT(DOW  FROM o.created_at)::int AS day_of_week
        FROM orders o
        WHERE o.outlet_id  = %(outlet_id)s
          AND o.status     != 'CANCELLED'
          AND o.created_at >= NOW() - INTERVAL '%(days)s days'
        GROUP BY DATE_TRUNC('hour', o.created_at),
                 EXTRACT(HOUR FROM o.created_at),
                 EXTRACT(DOW  FROM o.created_at)
        ORDER BY ds
    """
    return _query_to_df(sql, {"outlet_id": outlet_id, "days": days})


# ── Feature 4: No-show / cancel risk ───────────────────────────────────────────

def get_user_stats(user_id: int) -> dict:
    """
    Returns behavioural stats for a user needed by the no-show classifier.
    """
    sql = """
        SELECT
            COUNT(*)                                                          AS total_orders,
            SUM(CASE WHEN status = 'EXPIRED' THEN 1 ELSE 0 END)              AS no_show_count,
            SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END)            AS cancel_count,
            AVG(total_amount)                                                 AS avg_order_amount,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days')  AS orders_last_7d
        FROM orders
        WHERE student_id = %(user_id)s
          AND COALESCE(order_source, 'PLATFORM') = 'PLATFORM'
    """
    df = _query_to_df(sql, {"user_id": user_id})
    if df.empty or df.iloc[0]["total_orders"] == 0:
        return {
            "total_orders": 0,
            "no_show_rate": 0.1,    # neutral prior for new users
            "cancel_rate": 0.0,
            "avg_order_amount": 80.0,
            "orders_last_7d": 0,
        }
    row = df.iloc[0]
    total = max(1, int(row["total_orders"]))
    return {
        "total_orders": total,
        "no_show_rate": round(float(row["no_show_count"] or 0) / total, 4),
        "cancel_rate": round(float(row["cancel_count"] or 0) / total, 4),
        "avg_order_amount": float(row["avg_order_amount"] or 80.0),
        "orders_last_7d": int(row["orders_last_7d"] or 0),
    }


def get_no_show_training_data(days: int = 90) -> pd.DataFrame:
    """
    Returns labelled training data for no-show classifier.
    Label: 1 = no-show (EXPIRED status), 0 = picked up

    Columns: user_id, order_amount, slot_hour, total_orders, no_show_rate,
             orders_last_7d, label
    """
    sql = """
        WITH user_stats AS (
            SELECT
                student_id,
                COUNT(*)                                                     AS total_orders,
                SUM(CASE WHEN status = 'EXPIRED'  THEN 1 ELSE 0 END)        AS no_shows,
                COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') AS recent_orders
            FROM orders
            WHERE student_id IS NOT NULL
              AND COALESCE(order_source, 'PLATFORM') = 'PLATFORM'
            GROUP BY student_id
        )
        SELECT
            o.student_id                                           AS user_id,
            o.total_amount                                         AS order_amount,
            EXTRACT(HOUR FROM COALESCE(
                ps.start_time::time,
                o.ready_at::time
            ))::int                                                AS slot_hour,
            us.total_orders,
            ROUND((us.no_shows::float / GREATEST(us.total_orders, 1))::numeric, 4)
                                                                   AS no_show_rate,
            us.recent_orders                                       AS orders_last_7d,
            CASE WHEN o.status = 'EXPIRED' THEN 1 ELSE 0 END      AS label
        FROM orders o
        JOIN user_stats us ON us.student_id = o.student_id
        LEFT JOIN pickup_slots ps ON ps.id = o.pickup_slot_id
        WHERE o.student_id IS NOT NULL
          AND o.status IN ('PICKED', 'EXPIRED')
          AND o.created_at >= NOW() - INTERVAL '%(days)s days'
          AND COALESCE(o.order_source, 'PLATFORM') = 'PLATFORM'
    """
    return _query_to_df(sql, {"days": days})


# ── Feature 5: Menu analytics ──────────────────────────────────────────────────

def get_outlet_order_items(outlet_id: int, days: int = 30) -> pd.DataFrame:
    """
    Returns item-level order data for a specific outlet.
    Used for association rule mining and performance analytics.

    Columns: order_id, menu_item_id, item_name, quantity, price_at_order,
             created_at, order_source
    """
    sql = """
        SELECT
            o.id                                        AS order_id,
            oi.menu_item_id,
            mi.name                                     AS item_name,
            oi.quantity,
            oi.price_at_order,
            o.created_at,
            COALESCE(o.order_source, 'PLATFORM')        AS order_source
        FROM order_items oi
        JOIN orders      o   ON oi.order_id     = o.id
        JOIN menu_items  mi  ON oi.menu_item_id = mi.id
        WHERE o.outlet_id   = %(outlet_id)s
          AND o.status      != 'CANCELLED'
          AND o.created_at  >= NOW() - INTERVAL '%(days)s days'
        ORDER BY o.created_at DESC
    """
    return _query_to_df(sql, {"outlet_id": outlet_id, "days": days})


def get_trending_items(outlet_id: int, campus_id: int, days: int = 7, limit: int = 10) -> list[dict]:
    """
    Returns the most ordered items in the past `days` days for an outlet.
    Used as cold-start fallback for recommendations.
    """
    sql = """
        SELECT
            oi.menu_item_id,
            mi.name,
            SUM(oi.quantity)  AS total_ordered,
            COUNT(DISTINCT o.id) AS order_frequency
        FROM order_items oi
        JOIN orders     o   ON oi.order_id     = o.id
        JOIN menu_items mi  ON oi.menu_item_id = mi.id
        WHERE o.outlet_id   = %(outlet_id)s
          AND o.status      != 'CANCELLED'
          AND o.created_at  >= NOW() - INTERVAL '%(days)s days'
        GROUP BY oi.menu_item_id, mi.name
        ORDER BY total_ordered DESC
        LIMIT %(limit)s
    """
    df = _query_to_df(sql, {"outlet_id": outlet_id, "days": days, "limit": limit})
    if df.empty:
        return []
    return df.to_dict("records")