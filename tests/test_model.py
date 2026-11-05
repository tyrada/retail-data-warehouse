from decimal import Decimal

import pandas as pd
import pytest

from retail_warehouse.model import prepare_warehouse_frames


def source_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["T1", "2025-01-01", "C1", "Alice", "Consumer", "P1", "Mouse", "Electronics", "2", "10.25"],
            ["T2", "2025-01-01", "C1", "Alice", "Consumer", "P2", "Mug", "Home", "1", "5.00"],
            ["T3", "2025-02-01", "C2", "Bob", "Corporate", "P1", "Mouse", "Electronics", "3", "10.25"],
        ],
        columns=(
            "transaction_id", "sale_date", "customer_id", "customer_name", "segment",
            "product_id", "product_name", "category", "quantity", "unit_price",
        ),
    )


def test_builds_dimensions_at_expected_grain_and_reconciles_revenue():
    frames = prepare_warehouse_frames(source_frame())
    assert len(frames.customers) == 2
    assert len(frames.products) == 2
    assert len(frames.dates) == 2
    assert len(frames.facts) == 3
    assert frames.facts["revenue"].sum() == Decimal("56.25")
    assert set(frames.facts["customer_id"]) <= set(frames.customers["customer_id"])
    assert set(frames.facts["product_id"]) <= set(frames.products["product_id"])
    assert set(frames.facts["date_key"]) <= set(frames.dates["date_key"])


def test_rejects_duplicate_transaction_keys():
    source = source_frame()
    source.loc[1, "transaction_id"] = "T1"
    with pytest.raises(ValueError, match="must be unique"):
        prepare_warehouse_frames(source)


def test_rejects_nonpositive_quantities():
    source = source_frame()
    source.loc[0, "quantity"] = "0"
    with pytest.raises(ValueError, match="positive integers"):
        prepare_warehouse_frames(source)

