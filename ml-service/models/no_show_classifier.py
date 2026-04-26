"""
models/no_show_classifier.py — No-show / order abandonment risk predictor.

Algorithm: RandomForestClassifier (scikit-learn)

WHY RANDOM FOREST OVER LOGISTIC REGRESSION?
  - Handles class imbalance better (most students DO pick up; no-shows are rare)
  - Naturally handles non-linear feature interactions without explicit engineering
  - Feature importances help explain predictions to managers
  - Logistic regression would work fine but needs more tuning on imbalanced classes

FEATURES (all available without user consent issues):
  - no_show_rate:    User's historical no-show rate (most predictive!)
  - total_orders:    Order experience (new users → higher uncertainty)
  - order_amount:    Higher-value orders → users more likely to pick up
  - slot_hour:       Lunch rush (12-13) vs evening (18-19) vs other
  - orders_last_7d:  Recent activity = engaged user
  - cancel_rate:     Historical cancellation tendency

IMBALANCE HANDLING: class_weight="balanced" in RandomForest automatically
  up-weights the minority class (no-shows).

OUTPUT: probability ∈ [0, 1] + risk level label + recommendation for manager
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MIN_TRAINING_ROWS = 50

# Risk thresholds (tunable)
HIGH_RISK_THRESHOLD = 0.65
MEDIUM_RISK_THRESHOLD = 0.35


class NoShowClassifier:
    """
    Global no-show risk classifier (shared across all campuses).
    Individual campus patterns are captured via user-level features.
    """

    def __init__(self):
        self.model: Optional[RandomForestClassifier] = None
        self.scaler: Optional[StandardScaler] = None
        self.is_fitted = False
        self.auc = None
        self.feature_names = [
            "no_show_rate",
            "total_orders",
            "order_amount",
            "slot_hour",
            "orders_last_7d",
            "cancel_rate",
            "is_peak_hour",
        ]

    def fit(self, df: pd.DataFrame) -> dict:
        """
        Train the classifier on historical order outcomes.

        Args:
            df: from get_no_show_training_data() — columns include:
                user_id, no_show_rate, total_orders, order_amount,
                slot_hour, orders_last_7d, cancel_rate, label

        Returns: dict with auc and n_samples
        """
        if df.empty or len(df) < MIN_TRAINING_ROWS:
            logger.warning("[no_show] Only %d rows — skipping training", len(df) if not df.empty else 0)
            return {"status": "insufficient_data"}

        df = df.copy()
        df["is_peak_hour"] = df["slot_hour"].apply(
            lambda h: 1 if h in [12, 13, 18, 19] else 0
        )

        # Fill missing values with safe defaults
        df["cancel_rate"] = df["cancel_rate"].fillna(0.0) if "cancel_rate" in df.columns else 0.0
        df["no_show_rate"] = df["no_show_rate"].fillna(0.1)
        df["orders_last_7d"] = df["orders_last_7d"].fillna(0)

        X = df[self.feature_names].values.astype(float)
        y = df["label"].values.astype(int)

        # Check we have both classes
        if len(np.unique(y)) < 2:
            logger.warning("[no_show] Only one class in training data — skipping")
            return {"status": "single_class"}

        # ── Scale ─────────────────────────────────────────────────────────────
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # ── Train Random Forest ────────────────────────────────────────────────
        # n_estimators=200: stable predictions
        # max_depth=6: prevent overfitting on small datasets
        # class_weight="balanced": compensates for few no-shows in data
        # min_samples_leaf=5: prevents tiny leaves that overfit
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=6,
            class_weight="balanced",
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(X_scaled, y)

        # Cross-validated AUC (ROC-AUC, better than accuracy for imbalanced)
        try:
            cv_scores = cross_val_score(
                self.model, X_scaled, y,
                cv=min(3, len(df) // 20),
                scoring="roc_auc",
            )
            self.auc = round(float(cv_scores.mean()), 4)
        except Exception:
            self.auc = 0.5

        self.is_fitted = True

        # Log feature importances
        importances = dict(zip(self.feature_names, self.model.feature_importances_))
        logger.info(
            "[no_show] Trained | n=%d AUC=%.4f | top_feature=%s",
            len(df), self.auc,
            max(importances, key=importances.get)
        )
        return {"status": "trained", "n_samples": len(df), "auc": self.auc}

    def predict(
        self,
        no_show_rate: float,
        total_orders: int,
        order_amount: float,
        slot_hour: int,
        orders_last_7d: int,
        cancel_rate: float = 0.0,
    ) -> dict:
        """
        Predict no-show risk for a specific order.

        Returns:
            {
                "noShowProbability": 0.72,
                "riskLevel": "HIGH",
                "recommendation": "Consider advance payment lock"
            }
        """
        if not self.is_fitted or self.model is None:
            # Fallback: rule-based score using historical no-show rate
            prob = self._rule_based_score(no_show_rate, slot_hour, order_amount)
            return self._format_response(prob, strategy="rule_based")

        try:
            is_peak = 1 if slot_hour in [12, 13, 18, 19] else 0
            features = np.array([[
                no_show_rate,
                total_orders,
                order_amount,
                slot_hour,
                orders_last_7d,
                cancel_rate,
                is_peak,
            ]])

            features_scaled = self.scaler.transform(features)
            prob = float(self.model.predict_proba(features_scaled)[0][1])
            return self._format_response(prob, strategy="random_forest")

        except Exception as exc:
            logger.warning("[no_show] Prediction failed: %s", exc)
            prob = self._rule_based_score(no_show_rate, slot_hour, order_amount)
            return self._format_response(prob, strategy="rule_based_fallback")

    @staticmethod
    def _rule_based_score(no_show_rate: float, slot_hour: int, order_amount: float) -> float:
        """Simple rule-based fallback when model is not trained."""
        score = no_show_rate * 0.7
        if slot_hour in [12, 13, 18, 19]:
            score += 0.1  # peak hours → slightly higher no-show risk
        if order_amount < 30:
            score += 0.1  # very cheap orders → more likely to abandon
        return min(0.95, max(0.05, score))

    @staticmethod
    def _format_response(probability: float, strategy: str) -> dict:
        if probability >= HIGH_RISK_THRESHOLD:
            risk_level = "HIGH"
            recommendation = "Consider advance payment lock for this order"
        elif probability >= MEDIUM_RISK_THRESHOLD:
            risk_level = "MEDIUM"
            recommendation = "Send a pickup reminder 10 minutes before slot"
        else:
            risk_level = "LOW"
            recommendation = "No special action needed"

        return {
            "noShowProbability": round(probability, 4),
            "riskLevel": risk_level,
            "recommendation": recommendation,
            "strategy": strategy,
        }