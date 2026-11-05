"""Build dimension and fact-shaped frames before database loading."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import pandas as pd

SOURCE_COLUMNS = (
    "transaction_id", "sale_date", "customer_id", "customer_name", "segment",
    "product_id", "product_name", "category", "quantity", "unit_price",
)


@dataclass(frozen=True)
class WarehouseFrames:
    customers: pd.DataFrame
    products: pd.DataFrame
    dates: pd.DataFrame
    facts: pd.DataFrame


def prepare_warehouse_frames(source: pd.DataFrame) -> WarehouseFrames:
    missing = [column for column in SOURCE_COLUMNS if column not in source.columns]
    if missing:
        raise ValueError(f"missing source columns: {', '.join(missing)}")
    if source["transaction_id"].duplicated().any():
        raise ValueError("transaction_id values must be unique in the source")

    data = source.loc[:, SOURCE_COLUMNS].copy()
    dates = pd.to_datetime(data["sale_date"], format="%Y-%m-%d", errors="raise")
    quantities = pd.to_numeric(data["quantity"], errors="raise")
    if quantities.le(0).any() or quantities.mod(1).ne(0).any():
        raise ValueError("quantity values must be positive integers")
    try:
        prices = data["unit_price"].map(lambda value: Decimal(str(value)).quantize(Decimal("0.01")))
    except InvalidOperation as exc:
        raise ValueError("unit_price values must be valid decimals") from exc
    if prices.map(lambda value: value <= 0).any():
        raise ValueError("unit_price values must be positive")

    data["sale_date"] = dates.dt.date
    data["date_key"] = dates.dt.strftime("%Y%m%d").astype(int)
    data["quantity"] = quantities.astype(int)
    data["unit_price"] = prices
    data["revenue"] = data.apply(lambda row: row["unit_price"] * row["quantity"], axis=1)

    customers = data[["customer_id", "customer_name", "segment"]].drop_duplicates("customer_id").sort_values("customer_id")
    products = data[["product_id", "product_name", "category", "unit_price"]].drop_duplicates("product_id").sort_values("product_id")
    unique_dates = pd.Series(sorted(data["sale_date"].unique()), name="full_date")
    date_values = pd.to_datetime(unique_dates)
    date_dimension = pd.DataFrame(
        {
            "date_key": date_values.dt.strftime("%Y%m%d").astype(int),
            "full_date": date_values.dt.date,
            "day_of_month": date_values.dt.day,
            "month_number": date_values.dt.month,
            "month_name": date_values.dt.month_name(),
            "quarter_number": date_values.dt.quarter,
            "year_number": date_values.dt.year,
        }
    )
    facts = data[["transaction_id", "customer_id", "product_id", "date_key", "quantity", "unit_price", "revenue"]]
    return WarehouseFrames(customers.reset_index(drop=True), products.reset_index(drop=True), date_dimension, facts.reset_index(drop=True))

