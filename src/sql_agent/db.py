"""Synthetic sales DB (no personal data). Agent connections are read-only at the OS level."""
import random
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "data" / "sales.db"
REGIONS = ["EMEA", "NA", "APAC", "LATAM", "ANZ"]
CHANNELS = ["online", "retail", "wholesale"]
PRODUCTS = [("Alpine Ski", "Skis", 450.0), ("Trail Ski", "Skis", 380.0),
            ("Hike Boot", "Boots", 210.0), ("Ski Boot", "Boots", 320.0),
            ("Shell Jacket", "Apparel", 260.0), ("Beanie", "Accessories", 30.0)]


def seed(path: Path = DB, seed: int = 42, n_orders: int = 2000) -> None:
    rng = random.Random(seed)
    path.parent.mkdir(exist_ok=True)
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE products(id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL);
        CREATE TABLE orders(id INTEGER PRIMARY KEY, product_id INTEGER REFERENCES products(id),
            region TEXT, channel TEXT, qty INTEGER, order_date TEXT);""")
    con.executemany("INSERT INTO products(name,category,price) VALUES (?,?,?)", PRODUCTS)
    con.executemany(
        "INSERT INTO orders(product_id,region,channel,qty,order_date) VALUES (?,?,?,?,?)",
        [(rng.randint(1, len(PRODUCTS)), rng.choice(REGIONS), rng.choice(CHANNELS),
          rng.randint(1, 10), f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}")
         for _ in range(n_orders)])
    con.commit()
    con.close()


def connect_ro(path: Path = DB) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


if __name__ == "__main__":
    seed()
