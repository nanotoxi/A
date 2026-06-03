import sqlite3
import os
from datetime import date, timedelta
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "saneforce.db")


def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()


def run():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE reps (
        rep_id      INTEGER PRIMARY KEY,
        name        TEXT,
        role        TEXT CHECK(role IN ('sales_rep','manager','admin')),
        territory   TEXT,
        manager_id  INTEGER
    );

    CREATE TABLE stores (
        store_id        INTEGER PRIMARY KEY,
        store_name      TEXT,
        owner_name      TEXT,
        location        TEXT,
        territory       TEXT,
        rep_id          INTEGER REFERENCES reps(rep_id),
        last_visit_date TEXT,
        store_tier      TEXT
    );

    CREATE TABLE products (
        product_id      INTEGER PRIMARY KEY,
        product_name    TEXT,
        category        TEXT,
        sku             TEXT,
        price           REAL
    );

    CREATE TABLE sales (
        sale_id         INTEGER PRIMARY KEY,
        store_id        INTEGER REFERENCES stores(store_id),
        product_id      INTEGER REFERENCES products(product_id),
        rep_id          INTEGER REFERENCES reps(rep_id),
        units_sold      INTEGER,
        revenue         REAL,
        sale_date       TEXT,
        approach_used   TEXT
    );

    CREATE TABLE visits (
        visit_id        INTEGER PRIMARY KEY,
        store_id        INTEGER REFERENCES stores(store_id),
        rep_id          INTEGER REFERENCES reps(rep_id),
        visit_date      TEXT,
        outcome         TEXT,
        notes           TEXT
    );
    """)

    # Reps: 1 manager + 4 sales reps
    reps = [
        (1, "Arjun Mehta",   "manager",   "Mumbai",     None),
        (2, "Ravi Sharma",   "sales_rep", "Mumbai North", 1),
        (3, "Priya Nair",    "sales_rep", "Mumbai South", 1),
        (4, "Suresh Patil",  "sales_rep", "Pune",         1),
        (5, "Kavita Joshi",  "sales_rep", "Ahmedabad",    1),
    ]
    c.executemany("INSERT INTO reps VALUES (?,?,?,?,?)", reps)

    # Stores: 30 spread across territories
    stores = [
        # Mumbai North - rep 2
        (1,  "Sharma Kirana",         "Ramesh Sharma",   "Bandra",        "Mumbai North", 2, days_ago(9),  "B"),
        (2,  "City Mart",              "Sunil Kapoor",    "Andheri East",  "Mumbai North", 2, days_ago(3),  "A"),
        (3,  "Lucky General Store",   "Lucky Singh",     "Borivali",      "Mumbai North", 2, days_ago(14), "C"),
        (4,  "New India Stores",      "Harish Gupta",    "Malad",         "Mumbai North", 2, days_ago(2),  "A"),
        (5,  "Star Provisions",       "Dilip Rao",       "Kandivali",     "Mumbai North", 2, days_ago(6),  "B"),
        (6,  "Patel Brothers",        "Vijay Patel",     "Dahisar",       "Mumbai North", 2, days_ago(11), "C"),
        (7,  "Goregaon General",      "Anil Mishra",     "Goregaon",      "Mumbai North", 2, days_ago(4),  "B"),
        # Mumbai South - rep 3
        (8,  "Colaba Traders",        "Meena Iyer",      "Colaba",        "Mumbai South", 3, days_ago(1),  "A"),
        (9,  "Fort Provisions",       "Deepak Jain",     "Fort",          "Mumbai South", 3, days_ago(7),  "B"),
        (10, "Dadar Supermart",       "Sanjay Pawar",    "Dadar",         "Mumbai South", 3, days_ago(2),  "A"),
        (11, "Worli Kirana",          "Pankaj Shah",     "Worli",         "Mumbai South", 3, days_ago(13), "C"),
        (12, "Matunga Mart",          "Ramesh Kulkarni", "Matunga",       "Mumbai South", 3, days_ago(5),  "B"),
        (13, "Sion Stores",           "Geeta Desai",     "Sion",          "Mumbai South", 3, days_ago(3),  "B"),
        (14, "Chembur Choice",        "Prakash Naik",    "Chembur",       "Mumbai South", 3, days_ago(8),  "C"),
        # Pune - rep 4
        (15, "Koregaon Kirana",       "Mahesh Joshi",    "Koregaon Park", "Pune",         4, days_ago(10), "B"),
        (16, "Kothrud Provisions",    "Ashok Patil",     "Kothrud",       "Pune",         4, days_ago(2),  "A"),
        (17, "Hadapsar Mart",         "Nilesh Shinde",   "Hadapsar",      "Pune",         4, days_ago(6),  "B"),
        (18, "Viman Nagar Store",     "Santosh More",    "Viman Nagar",   "Pune",         4, days_ago(15), "C"),
        (19, "Baner General",         "Umesh Ghosh",     "Baner",         "Pune",         4, days_ago(3),  "A"),
        (20, "Aundh Superstore",      "Rekha Phadke",    "Aundh",         "Pune",         4, days_ago(1),  "A"),
        (21, "Wakad Kirana",          "Girish Lele",     "Wakad",         "Pune",         4, days_ago(12), "C"),
        # Ahmedabad - rep 5
        (22, "Navrangpura Stores",    "Hemant Shah",     "Navrangpura",   "Ahmedabad",    5, days_ago(2),  "A"),
        (23, "Vastrapur Mart",        "Jitendra Modi",   "Vastrapur",     "Ahmedabad",    5, days_ago(7),  "B"),
        (24, "Satellite Provisions",  "Chetna Trivedi",  "Satellite",     "Ahmedabad",    5, days_ago(4),  "B"),
        (25, "Bopal General",         "Paresh Bhatt",    "Bopal",         "Ahmedabad",    5, days_ago(16), "C"),
        (26, "Maninagar Kirana",      "Darshan Patel",   "Maninagar",     "Ahmedabad",    5, days_ago(3),  "A"),
        (27, "Gota Stores",           "Bhavna Rajput",   "Gota",          "Ahmedabad",    5, days_ago(9),  "B"),
        (28, "Chandkheda Mart",       "Kiran Solanki",   "Chandkheda",    "Ahmedabad",    5, days_ago(5),  "B"),
        (29, "Naranpura Provisions",  "Lalit Mehta",     "Naranpura",     "Ahmedabad",    5, days_ago(11), "C"),
        (30, "Thaltej General",       "Mitul Vyas",      "Thaltej",       "Ahmedabad",    5, days_ago(1),  "A"),
    ]
    c.executemany("INSERT INTO stores VALUES (?,?,?,?,?,?,?,?)", stores)

    # Products: 15 across 3 categories
    products = [
        (1,  "Shampoo 200ml",        "Personal Care", "SKU-201", 85.0),
        (2,  "Conditioner 150ml",    "Personal Care", "SKU-202", 75.0),
        (3,  "Body Lotion 300ml",    "Personal Care", "SKU-203", 120.0),
        (4,  "Shampoo 400ml",        "Personal Care", "SKU-204", 155.0),
        (5,  "Face Wash 100ml",      "Personal Care", "SKU-205", 95.0),
        (6,  "Mango Juice 1L",       "Beverages",     "SKU-301", 55.0),
        (7,  "Mixed Fruit 500ml",    "Beverages",     "SKU-302", 35.0),
        (8,  "Coconut Water 330ml",  "Beverages",     "SKU-303", 30.0),
        (9,  "Energy Drink 250ml",   "Beverages",     "SKU-304", 65.0),
        (10, "Green Tea 20 bags",    "Beverages",     "SKU-305", 90.0),
        (11, "Biscuits 100g",        "Snacks",        "SKU-101", 20.0),
        (12, "Namkeen Mix 200g",     "Snacks",        "SKU-102", 35.0),
        (13, "Chips 150g",           "Snacks",        "SKU-103", 25.0),
        (14, "Cookies 150g",         "Snacks",        "SKU-104", 45.0),
        (15, "Popcorn 100g",         "Snacks",        "SKU-105", 30.0),
    ]
    c.executemany("INSERT INTO products VALUES (?,?,?,?,?)", products)

    approaches = ["demo", "discount_offer", "relationship", "cold_visit"]

    # Sales records: 200+ over last 90 days
    # High-performing stores get more records; a few stores intentionally get zero/low records
    high_stores  = [2, 4, 8, 10, 16, 19, 20, 22, 26, 30]
    mid_stores   = [5, 7, 9, 12, 13, 17, 23, 24, 27, 28]
    low_stores   = [1, 3, 6, 11, 14, 15, 18, 21, 25, 29]

    sale_id = 1
    sales = []

    def store_rep(sid):
        return next(s[5] for s in stores if s[0] == sid)

    def add_sales(sid, count, units_range, days_range, approach_weights=None):
        nonlocal sale_id
        rep = store_rep(sid)
        for _ in range(count):
            pid = random.randint(1, 15)
            units = random.randint(*units_range)
            price = products[pid - 1][4]
            revenue = round(units * price, 2)
            sale_date = days_ago(random.randint(*days_range))
            approach = random.choices(approaches, weights=approach_weights or [1,1,1,1])[0]
            sales.append((sale_id, sid, pid, rep, units, revenue, sale_date, approach))
            sale_id += 1

    for s in high_stores:
        add_sales(s, random.randint(20, 30), (10, 40), (0, 90), [1, 3, 4, 1])
    for s in mid_stores:
        add_sales(s, random.randint(8, 15), (3, 15), (0, 90), [2, 2, 2, 1])
    for s in low_stores:
        add_sales(s, random.randint(2, 5), (1, 5), (7, 90), [1, 1, 2, 3])

    # Ensure stores 1 and 3 have NO sales in current week (for "underperforming" queries)
    # (already handled by days_range starting at 7 for low_stores)

    c.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?,?,?)", sales)

    # Visit logs: 60+
    visit_id = 1
    visits = []

    def add_visits(sid, count, days_range, outcomes):
        nonlocal visit_id
        rep = store_rep(sid)
        for i in range(count):
            visit_date = days_ago(random.randint(*days_range))
            outcome = random.choice(outcomes)
            notes = random.choice([
                "Owner was receptive, placed order",
                "Discussed new product range",
                "Price objection raised",
                "No stock issues, reorder done",
                "Owner unavailable, left samples",
                "Competitor products visible on shelf",
                "Good shelf placement achieved",
            ])
            visits.append((visit_id, sid, rep, visit_date, outcome, notes))
            visit_id += 1

    for s in high_stores:
        add_visits(s, 4, (1, 30), ["order_placed", "order_placed", "follow_up"])
    for s in mid_stores:
        add_visits(s, 3, (3, 60), ["order_placed", "follow_up", "no_order"])
    for s in low_stores:
        add_visits(s, 2, (8, 90), ["follow_up", "no_order", "no_order"])

    c.executemany("INSERT INTO visits VALUES (?,?,?,?,?,?)", visits)

    conn.commit()
    conn.close()

    print(f"Database seeded at {DB_PATH}")
    print(f"  Reps: {len(reps)}")
    print(f"  Stores: {len(stores)}")
    print(f"  Products: {len(products)}")
    print(f"  Sales records: {len(sales)}")
    print(f"  Visit logs: {len(visits)}")


if __name__ == "__main__":
    run()
