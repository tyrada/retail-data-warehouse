# Retail Data Warehouse

A compact local PostgreSQL warehouse that reshapes deterministic retail transactions into a star schema and exposes reporting views. It demonstrates dimensional modeling, surrogate keys, referential integrity, reconciliation, and idempotent fact loading without claiming cloud-warehouse experience.

## Architecture and grain

```text
seeded retail CSV -> Python validation/dimension shaping -> PostgreSQL
                                                       ├─ dim_customer
                                                       ├─ dim_product
                                                       ├─ dim_date
                                                       └─ fact_sales -> reporting views
```

The explicit grain of `fact_sales` is **one row per source retail transaction line item**. `transaction_id` is a unique natural key that makes reruns safe through `ON CONFLICT DO NOTHING`. Customer, product, and date dimensions use primary keys; every fact dimension key is a non-null foreign key. Positive quantity and price checks are enforced in both Python and SQL. Revenue is a stored generated column (`quantity * unit_price`).

See the [entity relationship diagram](docs/erd.md), complete [schema](sql/01_schema.sql), [views](sql/02_views.sql), and example [reporting queries](sql/reporting_queries.sql).

## Schema

- `dim_customer`: customer natural ID, name, and segment.
- `dim_product`: product natural ID, name, category, and current descriptive price.
- `dim_date`: integer `YYYYMMDD` key and calendar attributes.
- `fact_sales`: transaction key, dimension foreign keys, quantity, transaction-time price, generated revenue, and load timestamp.
- `vw_daily_revenue`, `vw_product_performance`, and `vw_customer_activity`: reusable reporting layers.

An operational normalized model typically separates customers, orders, order items, and products to reduce update duplication and preserve transaction workflows. A dimensional model intentionally denormalizes descriptive context around a measurable fact, making common analytical joins and aggregations simpler. This project is a reporting model, not an order-entry system.

## Local setup and run

Prerequisites: Python 3.11+ and Docker Compose.

```bash
cp .env.example .env
# Replace the local password in both POSTGRES_PASSWORD and DATABASE_URL.
python -m venv .venv
source .venv/bin/activate                # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'

generate-warehouse-data --rows 5000 --seed 2025
load-retail-warehouse preview --input data/retail_sales.csv

docker compose up -d
export DATABASE_URL='postgresql://warehouse_app:replace-with-local-password@localhost:5432/retail_dw'
load-retail-warehouse init-db
load-retail-warehouse load --input data/retail_sales.csv
load-retail-warehouse load --input data/retail_sales.csv
```

The Compose image initializes schema and views on a new volume; `init-db` is idempotent and also updates existing volumes. Verify that the second load inserted zero facts:

```bash
docker compose exec postgres psql -U warehouse_app -d retail_dw -c \
  "SELECT COUNT(*) AS facts, SUM(revenue) AS revenue FROM fact_sales;"
docker compose exec postgres psql -U warehouse_app -d retail_dw -f /dev/stdin < sql/reporting_queries.sql
```

Run fast local tests or the real PostgreSQL test separately:

```bash
pytest -m "not integration"
TEST_DATABASE_URL="$DATABASE_URL" pytest -m integration -v
```

GitHub Actions supplies a PostgreSQL 16 service and runs the full suite. The integration test loads the same file twice, verifies 100 facts then zero new facts, reconciles fact and view revenue, and confirms a broken foreign key is rejected.

## Actual results

Verified locally on November 5, 2026 with Python 3.12.16 and seed `2025`:

| Preview metric | Result |
| --- | ---: |
| Source/fact rows | 5,000 |
| Customer dimension rows | 994 |
| Product dimension rows | 30 |
| Date dimension rows | 731 |
| Reconciled source revenue | $481,364.75 |

Test result: **4 passed, 1 skipped**, with **56% total statement coverage**. The skipped test requires `TEST_DATABASE_URL`. Docker and PostgreSQL were not installed in this development environment, so database row counts, constraints, and view outputs were not locally measured. The commands and CI test above perform that verification; no database result is invented here.

## Scope and cleanup

This is a local PostgreSQL project, not Amazon Redshift and not an AWS deployment. It has no mocked AWS layer, IAM policy, or cloud cost. Credentials use ordinary environment variables and `.env` is ignored.

```bash
docker compose down             # keep the database volume
docker compose down --volumes   # destructive: remove the local warehouse data
```

## Limitations

- Dimensions are Type 1: corrected names or segments overwrite current attributes rather than keeping history.
- Row-wise parameterized inserts favor clarity over bulk `COPY` performance.
- There is no order-level fact, discount, tax, refund, or multi-currency handling.
- The date dimension only contains dates observed in the source.
- Concurrent loaders are not coordinated beyond database uniqueness constraints.

## Interview questions and answers

1. **Why state the fact grain first?** It defines what one row means, which dimensions apply, and which aggregations avoid double-counting.
2. **Why use surrogate dimension keys?** They decouple facts from mutable source identifiers and enable historical dimension strategies later.
3. **How is loading idempotent?** The unique `transaction_id` constraint and `ON CONFLICT DO NOTHING` prevent a rerun from adding the same fact.
4. **Why store fact price when product has a current price?** Transaction-time price is an immutable measurement; a product's current descriptive price may change.
5. **How is revenue reconciled?** Tests calculate source quantity times price, compare the loaded fact total, and compare that total with the daily reporting view.
