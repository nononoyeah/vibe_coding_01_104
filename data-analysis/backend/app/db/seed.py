from __future__ import annotations

from app.config import settings
from app.db.database import open_biz_connection
from app.paths import resolve_data_path


def ensure_biz_db() -> None:
    path = resolve_data_path(settings.biz_db_path)
    if path.exists() and path.stat().st_size > 0:
        return
    seed_biz_db()


def seed_biz_db() -> None:
    conn = open_biz_connection()
    try:
        conn.executescript(
            """
            DROP TABLE IF EXISTS order_items;
            DROP TABLE IF EXISTS orders;
            DROP TABLE IF EXISTS products;
            DROP TABLE IF EXISTS customers;

            CREATE TABLE customers (
              id INTEGER PRIMARY KEY,
              name TEXT NOT NULL,
              city TEXT NOT NULL
            );

            CREATE TABLE products (
              id INTEGER PRIMARY KEY,
              name TEXT NOT NULL,
              category TEXT NOT NULL,
              price REAL NOT NULL
            );

            CREATE TABLE orders (
              id INTEGER PRIMARY KEY,
              customer_id INTEGER NOT NULL,
              order_date TEXT NOT NULL,
              total_amount REAL NOT NULL,
              FOREIGN KEY(customer_id) REFERENCES customers(id)
            );

            CREATE TABLE order_items (
              id INTEGER PRIMARY KEY,
              order_id INTEGER NOT NULL,
              product_id INTEGER NOT NULL,
              quantity INTEGER NOT NULL,
              unit_price REAL NOT NULL,
              FOREIGN KEY(order_id) REFERENCES orders(id),
              FOREIGN KEY(product_id) REFERENCES products(id)
            );
            """
        )
        conn.executemany(
            "INSERT INTO customers(id, name, city) VALUES(?, ?, ?);",
            [
                (1, "张三", "上海"),
                (2, "李四", "北京"),
                (3, "王五", "上海"),
                (4, "赵六", "广州"),
            ],
        )
        conn.executemany(
            "INSERT INTO products(id, name, category, price) VALUES(?, ?, ?, ?);",
            [
                (1, "笔记本电脑", "数码", 5999.0),
                (2, "无线鼠标", "数码", 89.0),
                (3, "办公椅", "家居", 499.0),
                (4, "咖啡豆", "食品", 68.0),
            ],
        )
        conn.executemany(
            "INSERT INTO orders(id, customer_id, order_date, total_amount) VALUES(?, ?, ?, ?);",
            [
                (101, 1, "2026-01-15", 1200000.0),
                (102, 1, "2026-02-20", 2000000.0),
                (103, 2, "2026-02-28", 880000.0),
                (104, 3, "2026-03-10", 1500000.0),
                (105, 3, "2026-04-05", 800000.0),
                (106, 4, "2026-05-12", 700000.0),
                (107, 1, "2026-06-01", 1100000.0),
            ],
        )
        conn.executemany(
            "INSERT INTO order_items(id, order_id, product_id, quantity, unit_price) VALUES(?, ?, ?, ?, ?);",
            [
                (1, 101, 1, 2, 5999.0),
                (2, 102, 1, 3, 5999.0),
                (3, 103, 2, 10, 89.0),
                (4, 104, 3, 3, 499.0),
                (5, 105, 4, 12, 68.0),
                (6, 106, 2, 8, 89.0),
                (7, 107, 1, 1, 5999.0),
            ],
        )
        conn.commit()
    finally:
        conn.close()
