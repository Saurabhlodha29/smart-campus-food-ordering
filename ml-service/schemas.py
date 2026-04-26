"""
schemas.py — Pydantic request / response models for the ML service.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Prediction ────────────────────────────────────────────────────────────────

class DemandScoreRequest(BaseModel):
    menu_item_id: int   = Field(..., gt=0,  example=4)
    expires_at:   datetime = Field(
        ...,
        example="2025-03-15T15:30:00",
        description="ISO-8601 datetime — usually the order's expiresAt field"
    )


class DemandScoreResponse(BaseModel):
    menu_item_id: int
    expires_at:   datetime
    demand_score: float   = Field(..., description="Score clamped to [0.1, 0.9]")
    penalty:      float   = Field(..., description="50 × (1 − demand_score)")
    strategy:     str     = Field(..., description="gradient_boosting | rule_based_window | cold_start_default")
    confidence:   str     = Field(..., description="high | medium | low | none")


# ── Bulk prediction ───────────────────────────────────────────────────────────

class BulkDemandRequest(BaseModel):
    items: list[DemandScoreRequest] = Field(..., min_length=1)


class BulkDemandResponse(BaseModel):
    results:     list[DemandScoreResponse]
    avg_score:   float
    avg_penalty: float


# ── Model info ────────────────────────────────────────────────────────────────

class ModelInfoResponse(BaseModel):
    trained_at:    Optional[datetime]
    n_rows:        int
    n_items:       int
    model_type:    str
    mae:           float
    feature_names: list[str]
    is_ready:      bool


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:    str
    db_ok:     bool
    model_ok:  bool
    version:   str = "1.0.0"