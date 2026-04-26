"""
database.py — Database connectivity for the ML service (v1.0 original).
"""

import logging
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME",     "campus_food_dev"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "Project@291231"),
}

def ping() -> bool:
    """Check if the database is reachable."""
    try:
        conn = psycopg2.connect(**DB_CONFIG, connect_timeout=3)
        conn.close()
        return True
    except Exception as exc:
        logger.error("Database ping failed: %s", exc)
        return False

def get_conn():
    """Get a raw psycopg2 connection."""
    return psycopg2.connect(**DB_CONFIG)
