"""
scheduler.py — APScheduler retraining jobs for all ML models.

This module EXTENDS the existing hourly retraining in main.py.
It adds separate schedules for each new ML feature with appropriate cadence:

  Recommender         → every 24 hours at 3:00 AM (most expensive, runs once/day)
  Wait time model     → every 12 hours at 2:00 AM and 2:00 PM
  No-show classifier  → every 24 hours at 3:30 AM
  Demand forecast     → every 24 hours at 4:00 AM (per outlet)

The existing demand-score model schedule (hourly) in main.py is UNCHANGED.

Usage (called from main.py lifespan):
    from scheduler import setup_new_model_jobs
    setup_new_model_jobs(scheduler)   # pass in the existing APScheduler instance
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


def setup_new_model_jobs(scheduler: "BackgroundScheduler") -> None:
    """
    Register all new ML model retraining jobs on the provided scheduler.
    Call this once from main.py's lifespan, AFTER the existing jobs are set up.
    """

    # ── Recommender: every 24h at 3:00 AM ────────────────────────────────────
    scheduler.add_job(
        _retrain_recommender_job,
        trigger="cron",
        hour=3, minute=0,
        id="daily_recommender_retrain",
        replace_existing=True,
        misfire_grace_time=600,     # 10 min grace if server was sleeping
    )
    logger.info("[scheduler] Recommender retrain: daily at 03:00")

    # ── Wait time model: every 12h at 2:00 AM and 2:00 PM ────────────────────
    scheduler.add_job(
        _retrain_wait_time_job,
        trigger="cron",
        hour="2,14", minute=0,
        id="twicedaily_wait_time_retrain",
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("[scheduler] Wait time retrain: 02:00 and 14:00")

    # ── No-show classifier: every 24h at 3:30 AM ─────────────────────────────
    scheduler.add_job(
        _retrain_no_show_job,
        trigger="cron",
        hour=3, minute=30,
        id="daily_no_show_retrain",
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("[scheduler] No-show retrain: daily at 03:30")

    # ── Demand forecast: every 24h at 4:00 AM ────────────────────────────────
    scheduler.add_job(
        _retrain_forecast_job,
        trigger="cron",
        hour=4, minute=0,
        id="daily_forecast_retrain",
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("[scheduler] Forecast retrain: daily at 04:00")


# ── Job functions (called by APScheduler in background thread) ────────────────

def _retrain_recommender_job() -> None:
    logger.info("[scheduler] Recommender retrain triggered")
    try:
        from routers.recommendations import train_all_campuses
        train_all_campuses()
        logger.info("[scheduler] Recommender retrain complete")
    except Exception as exc:
        logger.error("[scheduler] Recommender retrain FAILED: %s", exc)


def _retrain_wait_time_job() -> None:
    logger.info("[scheduler] Wait time model retrain triggered")
    try:
        from routers.wait_time import train_wait_time_model
        metrics = train_wait_time_model()
        logger.info("[scheduler] Wait time retrain complete: %s", metrics)
    except Exception as exc:
        logger.error("[scheduler] Wait time retrain FAILED: %s", exc)


def _retrain_no_show_job() -> None:
    logger.info("[scheduler] No-show classifier retrain triggered")
    try:
        from routers.no_show import train_no_show_model
        metrics = train_no_show_model()
        logger.info("[scheduler] No-show retrain complete: %s", metrics)
    except Exception as exc:
        logger.error("[scheduler] No-show retrain FAILED: %s", exc)


def _retrain_forecast_job() -> None:
    """Retrain demand forecast for all active outlets."""
    logger.info("[scheduler] Demand forecast retrain triggered")
    try:
        from database_connector import _query_to_df
        from routers.slot_forecast import train_forecast_model

        df = _query_to_df("SELECT DISTINCT id FROM outlets WHERE status = 'ACTIVE'")
        if df.empty:
            logger.info("[scheduler] No active outlets for forecast retrain")
            return

        for outlet_id in df["id"].tolist():
            try:
                metrics = train_forecast_model(int(outlet_id))
                logger.debug("[scheduler] Forecast outlet=%s: %s", outlet_id, metrics)
            except Exception as exc:
                logger.warning("[scheduler] Forecast failed outlet=%s: %s", outlet_id, exc)

        logger.info("[scheduler] Forecast retrain complete for %d outlets", len(df))
    except Exception as exc:
        logger.error("[scheduler] Forecast retrain FAILED: %s", exc)


# ── Startup training: train all new models once at service start ──────────────

def run_startup_training() -> None:
    """
    Run initial training for all new models at service startup.
    Called from main.py lifespan AFTER the DB ping succeeds.
    Each job is wrapped individually so one failure doesn't block others.
    """
    logger.info("[startup] Training new ML models…")

    jobs = [
        ("wait_time", _retrain_wait_time_job),
        ("no_show", _retrain_no_show_job),
        ("recommender", _retrain_recommender_job),
        ("forecast", _retrain_forecast_job),
    ]

    for name, fn in jobs:
        try:
            logger.info("[startup] Training %s…", name)
            fn()
        except Exception as exc:
            logger.error("[startup] %s training failed (non-fatal): %s", name, exc)

    logger.info("[startup] New model startup training complete")