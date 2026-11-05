"""Transactional, idempotent PostgreSQL warehouse loader."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd
import psycopg

from retail_warehouse.model import prepare_warehouse_frames


def apply_sql(database_url: str, sql_dir: Path) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for path in sorted(sql_dir.glob("[0-9][0-9]_*.sql")):
                cursor.execute(path.read_text(encoding="utf-8"))


def load_warehouse(database_url: str, source_path: Path) -> dict[str, object]:
    frames = prepare_warehouse_frames(pd.read_csv(source_path, dtype=str))
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for row in frames.customers.itertuples(index=False):
                cursor.execute(
                    """INSERT INTO dim_customer (customer_id, customer_name, segment) VALUES (%s, %s, %s)
                       ON CONFLICT (customer_id) DO UPDATE SET customer_name = EXCLUDED.customer_name, segment = EXCLUDED.segment""",
                    tuple(row),
                )
            for row in frames.products.itertuples(index=False):
                cursor.execute(
                    """INSERT INTO dim_product (product_id, product_name, category, current_unit_price) VALUES (%s, %s, %s, %s)
                       ON CONFLICT (product_id) DO UPDATE SET product_name = EXCLUDED.product_name,
                       category = EXCLUDED.category, current_unit_price = EXCLUDED.current_unit_price""",
                    tuple(row),
                )
            for row in frames.dates.itertuples(index=False):
                cursor.execute(
                    """INSERT INTO dim_date (date_key, full_date, day_of_month, month_number, month_name, quarter_number, year_number)
                       VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (date_key) DO NOTHING""",
                    tuple(row),
                )

            inserted = 0
            for row in frames.facts.itertuples(index=False):
                cursor.execute(
                    """INSERT INTO fact_sales (transaction_id, customer_key, product_key, date_key, quantity, unit_price)
                       SELECT %s, c.customer_key, p.product_key, %s, %s, %s
                       FROM dim_customer c CROSS JOIN dim_product p
                       WHERE c.customer_id = %s AND p.product_id = %s
                       ON CONFLICT (transaction_id) DO NOTHING""",
                    (row.transaction_id, row.date_key, row.quantity, row.unit_price, row.customer_id, row.product_id),
                )
                inserted += cursor.rowcount
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(revenue), 0) FROM fact_sales")
            total_facts, total_revenue = cursor.fetchone()
    return {"source_rows": len(frames.facts), "inserted_facts": inserted, "total_facts": total_facts, "total_revenue": str(total_revenue)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize or load the retail warehouse")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init-db")
    init.add_argument("--sql-dir", type=Path, default=Path("sql"))
    load = subparsers.add_parser("load")
    load.add_argument("--input", type=Path, default=Path("data/retail_sales.csv"))
    preview = subparsers.add_parser("preview")
    preview.add_argument("--input", type=Path, default=Path("data/retail_sales.csv"))
    args = parser.parse_args()

    if args.command == "preview":
        frames = prepare_warehouse_frames(pd.read_csv(args.input, dtype=str))
        print(json.dumps({"customers": len(frames.customers), "products": len(frames.products), "dates": len(frames.dates), "facts": len(frames.facts), "revenue": str(frames.facts["revenue"].sum())}, indent=2))
        return 0

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        parser.error("DATABASE_URL is required for database commands")
    if args.command == "init-db":
        apply_sql(database_url, args.sql_dir)
        print("warehouse schema and views applied")
    else:
        print(json.dumps(load_warehouse(database_url, args.input), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
