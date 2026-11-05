# Entity relationship diagram

```mermaid
erDiagram
    DIM_CUSTOMER ||--o{ FACT_SALES : purchases
    DIM_PRODUCT ||--o{ FACT_SALES : describes
    DIM_DATE ||--o{ FACT_SALES : occurs_on

    DIM_CUSTOMER {
        bigint customer_key PK
        text customer_id UK
        text customer_name
        text segment
    }
    DIM_PRODUCT {
        bigint product_key PK
        text product_id UK
        text product_name
        text category
        numeric current_unit_price
    }
    DIM_DATE {
        integer date_key PK
        date full_date UK
        smallint month_number
        smallint quarter_number
        smallint year_number
    }
    FACT_SALES {
        bigint sales_key PK
        text transaction_id UK
        bigint customer_key FK
        bigint product_key FK
        integer date_key FK
        integer quantity
        numeric unit_price
        numeric revenue
    }
```

`fact_sales` has one row per source transaction line item. Its price is stored at transaction time; the product dimension's current price is descriptive and can change independently.

