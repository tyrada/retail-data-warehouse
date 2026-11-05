from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

from retail_warehouse.generator import generate_retail_data
from retail_warehouse.loader import apply_sql, load_warehouse


@pytest.mark.integration
def test_repeatable_load_constraints_and_revenue_reconciliation(tmp_path):
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set")
    root = Path(__file__).parents[1]
    apply_sql(database_url, root / "sql")
    source = tmp_path / "sales.csv"
    generate_retail_data(source, rows=100, seed=7)

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE fact_sales, dim_customer, dim_product, dim_date RESTART IDENTITY CASCADE")

    first = load_warehouse(database_url, source)
    second = load_warehouse(database_url, source)
    assert first["inserted_facts"] == 100
    assert second["inserted_facts"] == 0
    assert second["total_facts"] == 100

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT SUM(revenue) FROM fact_sales")
            fact_revenue = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(revenue) FROM vw_daily_revenue")
            view_revenue = cursor.fetchone()[0]
    assert fact_revenue == view_revenue == Decimal(second["total_revenue"])

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO fact_sales (transaction_id, customer_key, product_key, date_key, quantity, unit_price)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    ("BROKEN-FK", 999999, 999999, 20990101, 1, Decimal("1.00")),
                )

