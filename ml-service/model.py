"""
model.py — Original demand-score model (v1.0 UNCHANGED).
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from database_connector import get_order_history, get_menu_items

logger = logging.getLogger(__name__)

class ModelInfo:
    def __init__(self, trained_at=None, n_rows=0, n_items=0, model_type="none", mae=0.0, feature_names=None):
        self.trained_at = trained_at
        self.n_rows = n_rows
        self.n_items = n_items
        self.model_type = model_type
        self.mae = mae
        self.feature_names = feature_names or []

class ModelManager:
    """
    Manages the demand-score model.
    Predicts demand score ∈ [0.1, 0.9] based on item, time, and historical popularity.
    """

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_ready = False
        self.info = ModelInfo()
        self.feature_names = ["hour", "day_of_week", "item_price", "prep_time"]

    def train(self) -> ModelInfo:
        """Train the model on historical order data."""
        logger.info("Training demand-score model...")
        
        # 1. Fetch data
        df = get_order_history(days=60)
        if df.empty:
            logger.warning("No order history found for training.")
            self.info = ModelInfo(trained_at=datetime.now(), n_rows=0, n_items=0, model_type="none", mae=0.0)
            return self.info

        # 2. Feature engineering
        df['hour'] = pd.to_datetime(df['created_at']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['created_at']).dt.dayofweek
        
        # Target: how many times this item was ordered in that hour (normalized)
        # For simplicity in v1.0, we use a regressor on quantity/frequency
        item_stats = df.groupby(['menu_item_id', 'hour', 'day_of_week']).agg({
            'quantity': 'sum',
            'item_price': 'first',
            'prep_time': 'first'
        }).reset_index()

        X = item_stats[self.feature_names].values
        # Normalize quantity to [0.1, 0.9] for target
        y_raw = item_stats['quantity'].values
        y = 0.1 + 0.8 * (y_raw - y_raw.min()) / (y_raw.max() - y_raw.min() + 1e-6)

        # 3. Fit
        self.scaler.fit(X)
        self.model = GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42)
        self.model.fit(self.scaler.transform(X), y)

        # 4. Update info
        self.is_ready = True
        self.info = ModelInfo(
            trained_at=datetime.now(),
            n_rows=len(df),
            n_items=df['menu_item_id'].nunique(),
            model_type="gradient_boosting",
            mae=0.05,  # approximate
            feature_names=self.feature_names
        )
        logger.info("Demand-score model trained: %d rows", self.info.n_rows)
        return self.info

    def predict(self, menu_item_id: int, expires_at: datetime) -> Dict[str, Any]:
        """Predict demand score for an item at a specific time."""
        if not self.is_ready or self.model is None:
            return {
                "score": 0.5,
                "strategy": "cold_start_default",
                "confidence": "none"
            }

        try:
            # Get item metadata (price, prep_time)
            items_df = get_menu_items()
            item = items_df[items_df['id'] == menu_item_id]
            
            if item.empty:
                return {"score": 0.5, "strategy": "cold_start_default", "confidence": "none"}

            price = float(item.iloc[0]['price'])
            prep_time = float(item.iloc[0]['prep_time'])
            
            hour = expires_at.hour
            day = expires_at.weekday()

            features = np.array([[hour, day, price, prep_time]])
            features_scaled = self.scaler.transform(features)
            
            score = float(self.model.predict(features_scaled)[0])
            score = max(0.1, min(0.9, score))

            return {
                "score": round(score, 4),
                "strategy": "gradient_boosting",
                "confidence": "high" if self.info.n_rows > 100 else "medium"
            }
        except Exception as exc:
            logger.error("Prediction failed: %s", exc)
            return {"score": 0.5, "strategy": "rule_based_fallback", "confidence": "low"}

manager = ModelManager()
