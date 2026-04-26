"""
data_seeder.py — Synthetic data generator for demos and development.

Generates realistic-looking data for:
  - 5 outlets across 2 campuses
  - 50 menu items (10 per outlet)
  - 200 students
  - 2000 orders over 60 days
  - Realistic time patterns (peak at 12-1 PM, 6-7 PM)
  - ~15% COUNTER orders (walk-in customers)
  - ~8% no-show rate (EXPIRED orders)

Run:
    python data_seeder.py
    python data_seeder.py --orders 5000  # seed more orders

WARNING: This modifies your database. Only run on a dev/staging environment.
It checks for existing data before inserting and will skip seeding if data
already exists (safe to run multiple times).
"""

import argparse
import logging
import os
import random
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Seeder config ─────────────────────────────────────────────────────────────
CAMPUS_NAMES = ["IIT Delhi", "IIT Bombay"]
OUTLET_NAMES_BY_CAMPUS = [
    ["Dhaba Corner", "Quick Bites", "South Indian Express"],
    ["North Canteen", "Juice Bar"],
]
MENU_ITEMS_BY_OUTLET = [
    # Dhaba Corner
    [
        ("Chole Bhature", 60, 12), ("Dal Makhani", 80, 15), ("Paneer Butter Masala", 120, 18),
        ("Jeera Rice", 50, 10), ("Paratha", 40, 8), ("Mango Lassi", 45, 5),
        ("Masala Chai", 15, 3), ("Aloo Tikki", 30, 8), ("Samosa", 20, 5), ("Gulab Jamun", 25, 5),
    ],
    # Quick Bites
    [
        ("Veg Burger", 70, 8), ("Chicken Burger", 90, 10), ("French Fries", 50, 7),
        ("Cold Coffee", 60, 5), ("Sandwich", 55, 6), ("Pizza Slice", 80, 8),
        ("Pasta", 95, 12), ("Spring Roll", 45, 10), ("Maggi", 40, 8), ("Noodles", 65, 10),
    ],
    # South Indian Express
    [
        ("Masala Dosa", 70, 10), ("Plain Dosa", 50, 8), ("Idli Sambar", 45, 7),
        ("Uttapam", 65, 10), ("Vada", 35, 7), ("Coconut Chutney", 10, 2),
        ("Filter Coffee", 20, 3), ("Upma", 40, 8), ("Poha", 35, 7), ("Lemon Rice", 55, 8),
    ],
    # North Canteen
    [
        ("Rajma Chawal", 75, 10), ("Kadhi Pakora", 70, 12), ("Mix Veg", 80, 10),
        ("Roti", 10, 3), ("Naan", 20, 5), ("Butter Chicken", 130, 15),
        ("Chicken Biryani", 150, 20), ("Veg Biryani", 110, 18), ("Raita", 25, 3), ("Papad", 10, 2),
    ],
    # Juice Bar
    [
        ("Orange Juice", 50, 3), ("Watermelon Juice", 45, 3), ("Mixed Fruit Juice", 65, 4),
        ("Green Smoothie", 80, 5), ("Strawberry Shake", 90, 5),
        ("Banana Shake", 75, 5), ("Lassi", 40, 4), ("Nimbu Pani", 25, 2),
        ("Sugarcane Juice", 30, 3), ("Coconut Water", 35, 2),
    ],
]

STUDENT_NAMES = [
    "Arjun Sharma", "Priya Patel", "Rahul Gupta", "Sneha Verma", "Ankit Singh",
    "Pooja Nair", "Vikram Reddy", "Divya Iyer", "Rohan Kumar", "Meera Joshi",
    "Aditya Rao", "Kavya Menon", "Siddharth Mishra", "Riya Agarwal", "Harsh Tiwari",
    "Anjali Shah", "Nikhil Desai", "Shreya Bose", "Kunal Malhotra", "Nandita Kaur",
]

PAYMENT_MODES = ["ONLINE", "CASH"]
ORDER_STATUSES_NORMAL = ["PICKED"]
ORDER_STATUSES_WITH_NOSHOW = ["PICKED"] * 9 + ["EXPIRED"]  # 10% no-show


def _get_conn():
    import psycopg2
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "campus_food_dev"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "Project@291231"),
    )


def _check_existing_data(conn) -> bool:
    """Return True if seeded data already exists."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM orders")
        count = cur.fetchone()[0]
    return count > 100


def _weighted_hour() -> int:
    """Generate a realistic order hour weighted toward lunch and dinner peaks."""
    weights = [
        0, 0, 0, 0, 0, 0,       # 0-5 AM: no orders
        0.5, 1, 2, 3,            # 6-9 AM: light breakfast
        4, 6, 12, 12, 6,         # 10-14: lunch peak
        3, 2, 3, 8, 10,          # 15-19: evening peak
        5, 3, 1, 0.5,            # 20-23: light dinner
    ]
    return random.choices(range(24), weights=weights)[0]


def seed_data(n_orders: int = 2000) -> None:
    conn = _get_conn()

    if _check_existing_data(conn):
        logger.info("Database already has orders — skipping seed. Use --force to override.")
        conn.close()
        return

    logger.info("Starting seed with %d orders…", n_orders)
    cur = conn.cursor()

    # ── 1. Get campus IDs ────────────────────────────────────────────────────
    cur.execute("SELECT id FROM campuses ORDER BY id LIMIT 2")
    campus_rows = cur.fetchall()
    if not campus_rows:
        logger.error("No campuses found. Make sure the Spring Boot app has run DataInitializer.")
        conn.close()
        return
    campus_ids = [r[0] for r in campus_rows]
    logger.info("Found campuses: %s", campus_ids)

    # ── 2. Get outlet IDs ─────────────────────────────────────────────────────
    cur.execute("SELECT id FROM outlets WHERE status = 'ACTIVE' ORDER BY id")
    outlet_rows = cur.fetchall()
    if not outlet_rows:
        logger.error("No active outlets found. Launch some outlets first via the app.")
        conn.close()
        return
    outlet_ids = [r[0] for r in outlet_rows]
    logger.info("Found outlets: %s", outlet_ids)

    # ── 3. Get menu item IDs per outlet ───────────────────────────────────────
    outlet_items: dict[int, list[int]] = {}
    for oid in outlet_ids:
        cur.execute("SELECT id FROM menu_items WHERE outlet_id = %s AND is_available = true", (oid,))
        items = [r[0] for r in cur.fetchall()]
        if items:
            outlet_items[oid] = items
    logger.info("Menu items per outlet: %s", {k: len(v) for k, v in outlet_items.items()})

    # ── 4. Get student user IDs ───────────────────────────────────────────────
    cur.execute("SELECT id FROM users WHERE role_id = (SELECT id FROM roles WHERE name = 'STUDENT') LIMIT 200")
    student_rows = cur.fetchall()
    if not student_rows:
        logger.error("No student users found. Register some students first.")
        conn.close()
        return
    student_ids = [r[0] for r in student_rows]
    logger.info("Found %d students", len(student_ids))

    # ── 5. Seed orders ────────────────────────────────────────────────────────
    seeded = 0
    base_date = datetime.now() - timedelta(days=60)

    for _ in range(n_orders):
        outlet_id = random.choice(list(outlet_items.keys()))
        items_for_outlet = outlet_items[outlet_id]

        # Random order date/time with realistic distribution
        days_offset = random.randint(0, 59)
        hour = _weighted_hour()
        minute = random.randint(0, 59)
        order_time = base_date + timedelta(days=days_offset, hours=hour, minutes=minute)

        # PLATFORM vs COUNTER
        is_counter = random.random() < 0.15
        order_source = "COUNTER" if is_counter else "PLATFORM"
        student_id = None if is_counter else random.choice(student_ids)
        customer_name = random.choice(STUDENT_NAMES) + " (walk-in)" if is_counter else None

        # Order status (no-show only for PLATFORM)
        if is_counter:
            status = "PICKED"
        else:
            status = random.choice(ORDER_STATUSES_WITH_NOSHOW)

        # Randomly select 1-4 items
        n_items = random.choices([1, 2, 3, 4], weights=[40, 35, 15, 10])[0]
        chosen_items = random.sample(items_for_outlet, min(n_items, len(items_for_outlet)))

        # Fetch item prices
        cur.execute(
            "SELECT id, price, prep_time FROM menu_items WHERE id = ANY(%s)",
            (chosen_items,)
        )
        item_data = {r[0]: {"price": r[1], "prep_time": r[2]} for r in cur.fetchall()}

        total = sum(item_data[i]["price"] for i in chosen_items)
        avg_prep = sum(item_data[i].get("prep_time", 10) for i in chosen_items) // len(chosen_items)
        ready_at = order_time + timedelta(minutes=avg_prep + random.randint(-3, 8))
        expires_at = ready_at + timedelta(minutes=30)

        payment_mode = "CASH" if is_counter else random.choice(PAYMENT_MODES)
        payment_status = "PAID" if payment_mode == "ONLINE" or status == "PICKED" else "PENDING"

        # Insert order
        cur.execute("""
            INSERT INTO orders
                (student_id, outlet_id, status, total_amount, payment_mode, payment_status,
                 ready_at, expires_at, created_at, order_source, customer_name, pickup_otp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            student_id, outlet_id, status, total, payment_mode, payment_status,
            ready_at, expires_at, order_time, order_source, customer_name,
            str(random.randint(1000, 9999)),
        ))
        order_id = cur.fetchone()[0]

        # Insert order items
        for item_id in chosen_items:
            qty = random.choices([1, 2], weights=[80, 20])[0]
            cur.execute("""
                INSERT INTO order_items (order_id, menu_item_id, quantity, price_at_order)
                VALUES (%s, %s, %s, %s)
            """, (order_id, item_id, qty, item_data[item_id]["price"]))

        seeded += 1
        if seeded % 500 == 0:
            conn.commit()
            logger.info("Seeded %d / %d orders…", seeded, n_orders)

    conn.commit()
    cur.close()
    conn.close()
    logger.info("✅ Seeding complete: %d orders inserted", seeded)
    logger.info("Now restart the ML service to trigger model training on real data.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic order data for ML demos")
    parser.add_argument("--orders", type=int, default=2000, help="Number of orders to seed (default: 2000)")
    parser.add_argument("--force", action="store_true", help="Seed even if data already exists")
    args = parser.parse_args()

    if args.force:
        _check_existing_data = lambda _: False

    seed_data(n_orders=args.orders)