import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "saneforce.db")

SCHEMA = """
Tables:

reps(rep_id INTEGER PK, name TEXT, role TEXT ['sales_rep','manager','admin'], territory TEXT, manager_id INTEGER)

stores(store_id INTEGER PK, store_name TEXT, owner_name TEXT, location TEXT, territory TEXT,
       rep_id INTEGER FK reps, last_visit_date TEXT ISO date, store_tier TEXT ['A','B','C'])

products(product_id INTEGER PK, product_name TEXT, category TEXT, sku TEXT, price REAL)

sales(sale_id INTEGER PK, store_id INTEGER FK stores, product_id INTEGER FK products,
      rep_id INTEGER FK reps, units_sold INTEGER, revenue REAL, sale_date TEXT ISO date,
      approach_used TEXT ['demo','discount_offer','relationship','cold_visit'])

visits(visit_id INTEGER PK, store_id INTEGER FK stores, rep_id INTEGER FK reps,
       visit_date TEXT ISO date, outcome TEXT ['order_placed','follow_up','no_order'], notes TEXT)
"""


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_rep(rep_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM reps WHERE rep_id = ?", (rep_id,)).fetchone()
        return dict(row) if row else None


def is_db_ready():
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1 FROM reps LIMIT 1")
        return True
    except Exception:
        return False
