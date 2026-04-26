# Smart Campus ML Service — v2.0 README

## Overview

This is the Python FastAPI ML microservice for the Smart Campus Food Ordering platform.
It runs alongside the Spring Boot backend and provides 6 ML-powered features.

All original v1.0 endpoints work exactly as before — **nothing was removed or changed.**

---

## Setup

```bash
# 1. Create virtualenv (Python 3.11+ required)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Install sentiment analysis — pick one:
pip install transformers torch     # DistilBERT (recommended, ~260MB download)
# OR
pip install nltk                   # VADER (lightweight)

# 4. (Optional) Install association rules for combo suggestions:
pip install mlxtend

# 5. Copy your .env file (same credentials as application.yml)
cp .env.example .env
# Edit .env — same DB_HOST, DB_NAME, DB_USER, DB_PASSWORD as Spring Boot

# 6. Run
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### First run startup sequence

On first start, the service will:
1. Ping the database
2. Train the original demand-score model
3. Kick off background training for all 6 new models (in a daemon thread)

Training takes 10–60 seconds depending on data volume. While models are training,
every endpoint returns graceful fallback responses — no 500 errors.

---

## Seeding Demo Data

Before demoing, seed realistic synthetic data:

```bash
python data_seeder.py              # 2000 orders (default)
python data_seeder.py --orders 5000  # more orders for better ML
```

**Prerequisites:** At least 2 campuses, 2+ outlets (ACTIVE status), and some students
must exist in the database (created via the Spring Boot app first).

The seeder is idempotent — safe to run multiple times; it skips if data exists.

---

## API Documentation

Open **http://localhost:8000/docs** for interactive Swagger UI.

---

## Feature Reference

### Feature 1 — Personalised Recommendations

| Endpoint | Method | Description |
|---|---|---|
| `/recommend/food` | POST | Personalised items for a user at an outlet |
| `/recommend/trending` | GET | Trending items in last 7 days |
| `/recommend/retrain` | POST | Manually retrain recommender |

**Algorithm:** Hybrid = SVD Collaborative Filtering (50%) + TF-IDF Content-Based (30%) + Popularity (20%)

**Cold start:** Users with < 3 orders get popularity-based recommendations automatically.

**Request example:**
```json
POST /recommend/food
{
  "userId": 5,
  "outletId": 2,
  "campusId": 1,
  "limit": 5
}
```

**Response:**
```json
{
  "recommendations": [
    {"menuItemId": 12, "score": 0.94, "reason": "Highly recommended for you"},
    {"menuItemId": 7,  "score": 0.81, "reason": "Popular with students like you"}
  ],
  "strategy": "hybrid",
  "userId": 5,
  "outletId": 2
}
```

---

### Feature 2 — Dynamic Wait Time Prediction

| Endpoint | Method | Description |
|---|---|---|
| `/predict/wait-time` | POST | Predicted wait time for an order |

**Algorithm:** GradientBoostingRegressor — trained on (order_placed → ready_at) history.

**Pass `currentActiveOrders: -1`** to let the service query live DB queue depth.

```json
POST /predict/wait-time
{
  "outletId": 2,
  "orderItemCount": 3,
  "currentActiveOrders": -1
}
```

**Response:**
```json
{
  "estimatedMinutes": 18,
  "confidenceInterval": [13, 23],
  "strategy": "gradient_boosting",
  "outletId": 2
}
```

---

### Feature 3 — Slot Demand Forecasting

| Endpoint | Method | Description |
|---|---|---|
| `/forecast/slot-demand` | GET | Hourly order forecast for a specific date |
| `/forecast/peak-hours` | GET | Peak and low hours for an outlet |

**Algorithm:** SARIMA (seasonal ARIMA with daily seasonality). Falls back to historical hourly averages.

```
GET /forecast/slot-demand?outletId=2&date=2025-12-15
GET /forecast/peak-hours?outletId=2
```

---

### Feature 4 — No-Show Risk Prediction

| Endpoint | Method | Description |
|---|---|---|
| `/predict/no-show-risk` | POST | No-show probability for an order |

**Algorithm:** RandomForestClassifier with `class_weight="balanced"`.

**Risk levels:** HIGH (≥0.65) → require advance payment; MEDIUM → send reminder; LOW → no action.

```json
POST /predict/no-show-risk
{
  "userId": 5,
  "orderAmount": 120.0,
  "slotHour": 13,
  "minutesUntilSlot": 45
}
```

---

### Feature 5 — Menu Analytics

| Endpoint | Method | Description |
|---|---|---|
| `/analytics/menu-performance` | GET | Per-item performance metrics |
| `/analytics/combos` | GET | Frequently ordered together items |
| `/analytics/outlet-summary` | GET | Outlet health summary incl. PLATFORM vs COUNTER split |

Both PLATFORM and COUNTER orders contribute to analytics. Use `/analytics/outlet-summary`
to see the platform vs walk-in split for any outlet.

---

### Feature 6 — Sentiment-Aware Feedback (Future-Ready)

| Endpoint | Method | Description |
|---|---|---|
| `/feedback` | POST | Submit rating + text review |
| `/feedback/outlet` | GET | Aggregate sentiment for outlet |

**Sentiment pipeline:** DistilBERT → VADER → keyword fallback (auto-selected based on what's installed).

---

## Model Retraining Schedule

| Model | Schedule | Manual trigger |
|---|---|---|
| Demand score (v1) | Every 1 hour | `POST /model/retrain` |
| Recommender | Daily at 3:00 AM | `POST /recommend/retrain` |
| Wait time | Daily at 2:00 AM + 2:00 PM | `POST /predict/wait-time/retrain` |
| No-show | Daily at 3:30 AM | `POST /predict/no-show-risk/retrain` |
| Slot forecast | Daily at 4:00 AM | `POST /forecast/retrain?outletId=X` |

---

## Spring Boot Integration

Add to `application.yml`:
```yaml
ml:
  service:
    url: http://localhost:8000
    enabled: true
    timeout-ms: 3000
```

Replace `MLClient.java` with the new version in `ml-service/MLClient.java`.

New methods available:
- `mlClient.getRecommendations(userId, outletId, campusId)` → `List<Long>`
- `mlClient.predictWaitTime(outletId, itemCount, activeOrders)` → `int`
- `mlClient.getSlotDemandForecast(outletId, date)` → `Map<Integer, Integer>`
- `mlClient.predictNoShowRisk(userId, amount, slotHour)` → `double`
- `mlClient.getMenuPerformance(outletId)` → `List<Map<String, Object>>`

All methods have graceful fallbacks — safe to call even when ML service is down.

---

## Project Structure

```
ml-service/
├── main.py                  ← Entry point (replaces old main.py)
├── database.py              ← Original DB module (UNCHANGED)
├── database_connector.py    ← NEW: Extended DB access for all ML features
├── model.py                 ← Original demand-score model (UNCHANGED)
├── model_registry.py        ← NEW: Persistent model storage
├── scheduler.py             ← NEW: Retraining schedule for all models
├── data_seeder.py           ← NEW: Synthetic data generator
├── schemas.py               ← Original Pydantic schemas (UNCHANGED)
├── requirements.txt         ← Updated with new dependencies
├── MLClient.java            ← NEW: Updated Spring Boot client (copy to backend)
├── routers/
│   ├── recommendations.py   ← Feature 1
│   ├── wait_time.py         ← Feature 2
│   ├── slot_forecast.py     ← Feature 3
│   ├── no_show.py           ← Feature 4
│   ├── menu_analytics.py    ← Feature 5
│   └── feedback.py          ← Feature 6
└── models/
    ├── hybrid_recommender.py  ← SVD CF + TF-IDF CB + Popularity
    ├── wait_time_model.py     ← GradientBoostingRegressor
    ├── demand_forecast.py     ← SARIMA + hourly average fallback
    ├── no_show_classifier.py  ← RandomForestClassifier
    └── menu_analytics.py      ← Apriori association rules + stats
```

---

## Counter Orders & ML

Orders placed by managers at the counter (`order_source = "COUNTER"`) are:

- **Included** in wait-time training (they represent real kitchen load)
- **Included** in demand forecasting (real slot demand)
- **Included** in menu analytics (real sales data)
- **Excluded** from collaborative filtering (no user ID → can't model preferences)
- **Excluded** from no-show risk (walk-in customers don't have pickup slots)

The `analytics/outlet-summary` endpoint shows the PLATFORM vs COUNTER split
so managers can understand their true channel mix.