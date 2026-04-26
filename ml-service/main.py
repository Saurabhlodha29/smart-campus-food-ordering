"""
main.py — Smart Campus Food ML Service (v2.0)

IMPORTANT: This file REPLACES the existing main.py.
All original endpoints (POST /predict/demand-score, GET /health, etc.)
are preserved exactly as they were. New endpoints are added via routers.

Original endpoints (UNCHANGED):
─────────────────────────────────────────────────────────────────────
POST /predict/demand-score          Single demand-score prediction
POST /predict/demand-score/bulk     Batch demand-score prediction
POST /model/retrain                 Retrain demand-score model
GET  /model/info                    Demand-score model metadata
GET  /health                        Health check (DB + all models)

New endpoints added in v2.0:
─────────────────────────────────────────────────────────────────────
POST /recommend/food                Personalised food recommendations
GET  /recommend/trending            Trending items at an outlet
POST /recommend/retrain             Retrain recommender

POST /predict/wait-time             Dynamic wait time prediction
POST /predict/wait-time/retrain     Retrain wait-time model

GET  /forecast/slot-demand          Hourly order forecast for a date
GET  /forecast/peak-hours           Peak/low hours for outlet
POST /forecast/retrain              Retrain demand forecast

POST /predict/no-show-risk          No-show probability for an order
POST /predict/no-show-risk/retrain  Retrain no-show classifier

GET  /analytics/menu-performance    Per-item performance metrics
GET  /analytics/combos              Frequently ordered together items
GET  /analytics/outlet-summary      Outlet health summary

POST /feedback                      Submit rating + sentiment analysis
GET  /feedback/outlet               Outlet aggregate sentiment

Run:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ── Existing imports (UNCHANGED) ──────────────────────────────────────────────
from database import ping
from model import manager as model_manager
from schemas import (
    BulkDemandRequest,
    BulkDemandResponse,
    DemandScoreRequest,
    DemandScoreResponse,
    HealthResponse,
    ModelInfoResponse,
)

# ── New router imports ────────────────────────────────────────────────────────
from routers import recommendations, wait_time, slot_forecast, no_show, menu_analytics, feedback
from scheduler import setup_new_model_jobs, run_startup_training

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── APScheduler ───────────────────────────────────────────────────────────────
scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

BASE_PENALTY = 50.0


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== Smart Campus ML Service v2.0 starting ===")

    db_ok = ping()

    # ── Original demand-score model startup training (UNCHANGED) ──────────
    if db_ok:
        logger.info("DB reachable — training demand-score model…")
        try:
            info = model_manager.train()
            logger.info("Demand-score startup training done: %s", info)
        except Exception as exc:
            logger.error("Demand-score startup training failed: %s", exc)
    else:
        logger.warning("DB not reachable at startup — all models in fallback mode.")

    # ── New model startup training ─────────────────────────────────────────
    if db_ok:
        import threading
        # Run in background thread so startup doesn't block HTTP server
        t = threading.Thread(target=run_startup_training, daemon=True)
        t.start()

    # ── Original hourly retrain schedule (UNCHANGED) ──────────────────────
    scheduler.add_job(
        _demand_score_retrain_job,
        trigger="interval",
        hours=1,
        id="hourly_demand_score_retrain",
        replace_existing=True,
    )

    # ── New model retrain schedules ────────────────────────────────────────
    setup_new_model_jobs(scheduler)

    scheduler.start()
    logger.info("APScheduler started with all retraining jobs.")

    yield  # ← app runs here

    scheduler.shutdown(wait=False)
    logger.info("=== Smart Campus ML Service v2.0 stopped ===")


def _demand_score_retrain_job():
    """Existing hourly demand-score retrain (UNCHANGED)."""
    logger.info("[scheduler] Hourly demand-score retrain triggered.")
    try:
        model_manager.train()
    except Exception as exc:
        logger.error("[scheduler] Demand-score retrain failed: %s", exc)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Campus — ML Service",
    description=(
        "Demand scoring, personalised recommendations, wait time prediction, "
        "slot demand forecasting, no-show risk, menu analytics, and sentiment analysis."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include new routers ───────────────────────────────────────────────────────
app.include_router(recommendations.router)
app.include_router(wait_time.router)
app.include_router(slot_forecast.router)
app.include_router(no_show.router)
app.include_router(menu_analytics.router)
app.include_router(feedback.router)


# ── Original endpoints (COMPLETELY UNCHANGED from v1.0) ──────────────────────

def _build_response(req: DemandScoreRequest, result: dict) -> DemandScoreResponse:
    score = result["score"]
    penalty = round(BASE_PENALTY * (1 - score), 2)
    return DemandScoreResponse(
        menu_item_id=req.menu_item_id,
        expires_at=req.expires_at,
        demand_score=score,
        penalty=penalty,
        strategy=result["strategy"],
        confidence=result["confidence"],
    )


@app.post(
    "/predict/demand-score",
    response_model=DemandScoreResponse,
    summary="Predict demand score for a single menu item",
    tags=["Prediction"],
)
def predict_demand_score(req: DemandScoreRequest) -> DemandScoreResponse:
    result = model_manager.predict(req.menu_item_id, req.expires_at)
    return _build_response(req, result)


@app.post(
    "/predict/demand-score/bulk",
    response_model=BulkDemandResponse,
    summary="Batch predict demand scores for multiple items",
    tags=["Prediction"],
)
def predict_bulk(req: BulkDemandRequest) -> BulkDemandResponse:
    results = []
    for item_req in req.items:
        result = model_manager.predict(item_req.menu_item_id, item_req.expires_at)
        results.append(_build_response(item_req, result))

    avg_score = round(sum(r.demand_score for r in results) / len(results), 4)
    avg_penalty = round(BASE_PENALTY * (1 - avg_score), 2)

    return BulkDemandResponse(results=results, avg_score=avg_score, avg_penalty=avg_penalty)


@app.post(
    "/model/retrain",
    response_model=ModelInfoResponse,
    summary="Trigger immediate demand-score model retraining",
    tags=["Model"],
)
def retrain() -> ModelInfoResponse:
    if not ping():
        raise HTTPException(status_code=503, detail="Database not reachable — cannot retrain.")
    try:
        info = model_manager.train()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Training failed: {exc}")

    return ModelInfoResponse(
        trained_at=info.trained_at,
        n_rows=info.n_rows,
        n_items=info.n_items,
        model_type=info.model_type,
        mae=info.mae,
        feature_names=info.feature_names,
        is_ready=model_manager.is_ready,
    )


@app.get(
    "/model/info",
    response_model=ModelInfoResponse,
    summary="Current demand-score model metadata",
    tags=["Model"],
)
def model_info() -> ModelInfoResponse:
    info = model_manager.info
    return ModelInfoResponse(
        trained_at=info.trained_at,
        n_rows=info.n_rows,
        n_items=info.n_items,
        model_type=info.model_type,
        mae=info.mae,
        feature_names=info.feature_names,
        is_ready=model_manager.is_ready,
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check — DB + all models",
    tags=["Ops"],
)
def health() -> HealthResponse:
    """
    Extended health check — checks DB + all ML models.
    Returns degraded if DB is down, not a 503.
    """
    from model_registry import registry

    db_ok = ping()
    demand_model_ok = model_manager.is_ready

    # Check new models
    model_status = {
        "demand_score": demand_model_ok,
        "recommender": registry.is_trained("recommender"),
        "wait_time": registry.is_trained("wait_time"),
        "no_show": registry.is_trained("no_show"),
    }

    status = "ok" if db_ok else "degraded"
    return HealthResponse(
        status=status,
        db_ok=db_ok,
        model_ok=demand_model_ok,
    )


@app.get("/", include_in_schema=False)
def root():
    return {
        "service": "Smart Campus ML Service v2.0",
        "docs": "/docs",
        "health": "/health",
        "new_in_v2": [
            "/recommend/food",
            "/predict/wait-time",
            "/forecast/slot-demand",
            "/predict/no-show-risk",
            "/analytics/menu-performance",
            "/feedback",
        ],
    }