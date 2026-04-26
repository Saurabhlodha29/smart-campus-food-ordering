"""
models/hybrid_recommender.py — Hybrid food recommendation model.

Algorithm: Hybrid = Collaborative Filtering + Content-Based + Popularity Boost

WHY HYBRID?
  - Collaborative Filtering (CF) alone fails for cold-start users (< 3 orders)
  - Content-Based (CB) alone misses social signals (what similar students like)
  - Popularity boost ensures trending items always surface even for new users
  - Blending all three gives robust recommendations in all scenarios

COMPONENTS:
  1. Collaborative Filtering — SVD matrix factorisation via scikit-learn's
     TruncatedSVD on the user×item interaction matrix. Chosen over Surprise
     library because it works on sparse matrices natively and is faster.

  2. Content-Based — TF-IDF on item names + cosine similarity. If a user
     liked "Veg Burger", we surface items with similar name tokens.

  3. Popularity — items ordered most in the last 7 days get a score boost.

COLD START:
  Users with < MIN_ORDERS_FOR_CF orders fall back directly to popularity.

SCORING FORMULA:
  final_score = α × cf_score + β × cb_score + γ × popularity_score
  Default: α=0.5, β=0.3, γ=0.2  (tunable via env vars)

RETRAINING: triggered by APScheduler every 24 hours at 3 AM.
"""

import logging
import math
from functools import lru_cache
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)

# ── Hyper-parameters ──────────────────────────────────────────────────────────
MIN_ORDERS_FOR_CF = 3      # users below this get pure popularity
SVD_COMPONENTS = 20        # latent factors — keep low for small datasets
CF_WEIGHT = 0.50           # weight for collaborative score
CB_WEIGHT = 0.30           # weight for content-based score
POP_WEIGHT = 0.20          # weight for popularity score


class HybridRecommender:
    """
    Campus-scoped hybrid recommender. One instance per campus_id.
    """

    def __init__(self, campus_id: int):
        self.campus_id = campus_id
        self.svd: Optional[TruncatedSVD] = None
        self.tfidf: Optional[TfidfVectorizer] = None
        self.user_item_matrix: Optional[pd.DataFrame] = None
        self.item_embeddings: Optional[np.ndarray] = None
        self.item_tfidf_matrix = None
        self.popularity_scores: dict[int, float] = {}
        self.menu_items_df: Optional[pd.DataFrame] = None
        self.is_fitted = False

    def fit(
        self,
        user_item_matrix: pd.DataFrame,
        menu_items_df: pd.DataFrame,
        order_history_df: pd.DataFrame,
    ) -> dict:
        """
        Train all three recommendation components.

        Args:
            user_item_matrix: pivot (user_id × menu_item_id) of order quantities
            menu_items_df:    item metadata with columns: id, name, price, prep_time
            order_history_df: raw order history for popularity calculation

        Returns: dict of training metrics
        """
        if user_item_matrix.empty or menu_items_df.empty:
            logger.warning("[recommender campus=%s] Not enough data to train", self.campus_id)
            return {"status": "insufficient_data"}

        self.user_item_matrix = user_item_matrix
        self.menu_items_df = menu_items_df.set_index("id")

        # ── Component 1: Collaborative Filtering (SVD) ─────────────────────
        matrix = user_item_matrix.values.astype(float)

        # Normalise rows so prolific orderers don't dominate
        row_norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        row_norms[row_norms == 0] = 1
        matrix_normed = matrix / row_norms

        n_components = min(SVD_COMPONENTS, matrix.shape[0] - 1, matrix.shape[1] - 1)
        n_components = max(1, n_components)

        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        user_factors = self.svd.fit_transform(matrix_normed)
        # item_factors shape: (n_items, n_components)
        item_factors = self.svd.components_.T
        self.item_embeddings = item_factors  # used for item-to-item similarity

        # ── Component 2: Content-Based (TF-IDF on item names) ──────────────
        # Build text representation: "name name price_bucket preptime_bucket"
        # Repeating name gives it more weight in TF-IDF
        texts = []
        for _, row in menu_items_df.iterrows():
            price_bucket = "budget" if row["price"] < 50 else ("mid" if row["price"] < 150 else "premium")
            prep_bucket = "quick" if row.get("prep_time", 10) < 10 else "regular"
            text = f"{row['name']} {row['name']} {price_bucket} {prep_bucket}"
            texts.append(text)

        self.tfidf = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_features=500,
        )
        self.item_tfidf_matrix = self.tfidf.fit_transform(texts)

        # ── Component 3: Popularity (7-day order counts) ────────────────────
        if not order_history_df.empty:
            recent = order_history_df[
                order_history_df["created_at"] >= pd.Timestamp.now() - pd.Timedelta(days=7)
            ]
            if not recent.empty:
                pop = recent.groupby("menu_item_id")["quantity"].sum()
                max_pop = pop.max()
                if max_pop > 0:
                    self.popularity_scores = (pop / max_pop).to_dict()

        self.is_fitted = True

        n_users = user_item_matrix.shape[0]
        n_items = user_item_matrix.shape[1]
        logger.info(
            "[recommender campus=%s] Fitted | users=%d items=%d svd_components=%d",
            self.campus_id, n_users, n_items, n_components
        )
        return {
            "status": "trained",
            "n_users": n_users,
            "n_items": n_items,
            "svd_components": n_components,
        }

    def recommend(
        self,
        user_id: int,
        outlet_id: int,
        outlet_item_ids: list[int],
        user_order_count: int,
        limit: int = 5,
    ) -> list[dict]:
        """
        Generate personalised recommendations for a user at a specific outlet.

        Args:
            user_id:          The student's user ID
            outlet_id:        The outlet being browsed
            outlet_item_ids:  All item IDs available at this outlet
            user_order_count: Total orders placed by this user (for cold-start detection)
            limit:            How many items to return

        Returns: list of {menuItemId, score, reason}
        """
        if not outlet_item_ids:
            return []

        # ── Cold start: user has too few orders for CF ─────────────────────
        if not self.is_fitted or user_order_count < MIN_ORDERS_FOR_CF:
            return self._popularity_fallback(outlet_item_ids, limit, reason="Trending at this outlet")

        # ── Compute scores for each available outlet item ──────────────────
        scores = {}
        for item_id in outlet_item_ids:
            cf_score = self._cf_score(user_id, item_id)
            cb_score = self._cb_score(user_id, item_id)
            pop_score = self.popularity_scores.get(item_id, 0.0)

            final = CF_WEIGHT * cf_score + CB_WEIGHT * cb_score + POP_WEIGHT * pop_score
            scores[item_id] = final

        if not scores:
            return self._popularity_fallback(outlet_item_ids, limit)

        # Sort and build response
        top_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        result = []
        for item_id, score in top_items:
            if score <= 0:
                continue
            reason = self._pick_reason(score, pop_score=self.popularity_scores.get(item_id, 0))
            result.append({
                "menuItemId": item_id,
                "score": round(float(score), 4),
                "reason": reason,
            })

        # If we got fewer than requested, pad with popularity
        if len(result) < limit:
            seen_ids = {r["menuItemId"] for r in result}
            remaining = [i for i in outlet_item_ids if i not in seen_ids]
            result.extend(self._popularity_fallback(remaining, limit - len(result)))

        return result[:limit]

    # ── Internal scoring helpers ───────────────────────────────────────────────

    def _cf_score(self, user_id: int, item_id: int) -> float:
        """
        Collaborative filtering score for (user, item) using SVD.
        Returns predicted affinity in [0, 1].
        """
        if self.user_item_matrix is None or self.svd is None:
            return 0.0
        if user_id not in self.user_item_matrix.index:
            return 0.0
        if item_id not in self.user_item_matrix.columns:
            return 0.0

        try:
            user_row = self.user_item_matrix.loc[user_id].values.astype(float)
            norm = np.linalg.norm(user_row)
            if norm > 0:
                user_row = user_row / norm

            user_latent = self.svd.transform(user_row.reshape(1, -1))[0]
            item_idx = list(self.user_item_matrix.columns).index(item_id)
            item_latent = self.svd.components_[:, item_idx]

            score = float(np.dot(user_latent, item_latent))
            # Normalise to [0, 1] via sigmoid
            score = 1.0 / (1.0 + math.exp(-score * 3))
            return score
        except Exception:
            return 0.0

    def _cb_score(self, user_id: int, item_id: int) -> float:
        """
        Content-based score: cosine similarity between a candidate item
        and the user's historically liked items.
        """
        if (self.user_item_matrix is None or self.item_tfidf_matrix is None
                or user_id not in self.user_item_matrix.index):
            return 0.0

        try:
            # Items this user has ordered (non-zero columns)
            user_row = self.user_item_matrix.loc[user_id]
            liked_items = user_row[user_row > 0].index.tolist()
            if not liked_items:
                return 0.0

            all_items = list(self.user_item_matrix.columns)
            if item_id not in all_items:
                return 0.0

            candidate_idx = all_items.index(item_id)
            candidate_vec = self.item_tfidf_matrix[candidate_idx]

            # Average TF-IDF vector of liked items
            liked_idxs = [all_items.index(i) for i in liked_items if i in all_items]
            if not liked_idxs:
                return 0.0

            liked_matrix = self.item_tfidf_matrix[liked_idxs]
            user_profile = liked_matrix.mean(axis=0)

            sim = cosine_similarity(candidate_vec, user_profile)[0, 0]
            return float(max(0.0, sim))
        except Exception:
            return 0.0

    def _popularity_fallback(
        self, item_ids: list[int], limit: int, reason: str = "Popular at this outlet"
    ) -> list[dict]:
        """Return most popular items from the given list."""
        scored = [
            (iid, self.popularity_scores.get(iid, 0.0))
            for iid in item_ids
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {"menuItemId": iid, "score": round(s, 4), "reason": reason}
            for iid, s in scored[:limit]
        ]

    @staticmethod
    def _pick_reason(score: float, pop_score: float) -> str:
        if score > 0.7:
            return "Highly recommended for you"
        elif pop_score > 0.6:
            return "Popular with students like you"
        elif score > 0.4:
            return "You might enjoy this"
        else:
            return "Trending at this outlet"