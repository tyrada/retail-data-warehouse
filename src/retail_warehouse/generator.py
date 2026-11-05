"""Deterministic, clean retail source data for the warehouse loader."""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

PRODUCTS = [
    (f"P-{index:03d}", f"Product {index:02d}", ("Electronics", "Home", "Apparel", "Grocery")[index % 4], 5 + index * 1.75)
    for index in range(1, 31)
]
SEGMENTS = ("Consumer", "Corporate", "Small Business")


def generate_retail_data(output: Path, rows: int = 5_000, seed: int = 2025) -> None:
    rng = random.Random(seed)
    start = date(2024, 1, 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        "transaction_id", "sale_date", "customer_id", "customer_name", "segment",
        "product_id", "product_name", "category", "quantity", "unit_price",
    )
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(1, rows + 1):
            customer_number = rng.randint(1, 1_000)
            product_id, product_name, category, price = rng.choice(PRODUCTS)
            writer.writerow(
                {
                    "transaction_id": f"TX-{index:07d}",
                    "sale_date": (start + timedelta(days=rng.randrange(731))).isoformat(),
                    "customer_id": f"C-{customer_number:04d}",
                    "customer_name": f"Customer {customer_number:04d}",
                    "segment": SEGMENTS[customer_number % len(SEGMENTS)],
                    "product_id": product_id,
                    "product_name": product_name,
                    "category": category,
                    "quantity": rng.randint(1, 5),
                    "unit_price": f"{price:.2f}",
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic retail warehouse source data")
    parser.add_argument("--output", type=Path, default=Path("data/retail_sales.csv"))
    parser.add_argument("--rows", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=2025)
    args = parser.parse_args()
    generate_retail_data(args.output, args.rows, args.seed)
    print(f"generated {args.rows} rows at {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

