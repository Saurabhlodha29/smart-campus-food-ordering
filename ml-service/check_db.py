import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME",     "campus_food_dev"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "Project@291231"),
}

try:
    print(f"Connecting to {DB_CONFIG['host']}...")
    conn = psycopg2.connect(**DB_CONFIG, connect_timeout=5)
    print("Connected!")
    conn.close()
except Exception as e:
    print(f"Failed: {e}")
