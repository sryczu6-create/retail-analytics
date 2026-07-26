-- Sales fact: one row per invoice line (source grain).
-- FKs to the three dimensions, degenerate dim (invoice_no), flag, and measures.
--
-- DESIGN NOTE (BigQuery Sandbox constraint):
--   Ideally this fact is PARTITIONED BY invoice_date. But the Sandbox forces a
--   60-day partition expiration that cannot be disabled, which would immediately
--   empty partitions holding historical 2009-2011 dates. So in the Sandbox we
--   CLUSTER by invoice_date (plus transaction_type, customer_key) instead — this
--   still prunes date-range and segment scans, with no expiration.
--   In a billing-enabled project we would use:
--     partition_by={'field':'invoice_date','data_type':'date','granularity':'day'}
--   with partition_expiration_days disabled.

{{
  config(
    materialized='table',
    cluster_by=["invoice_date", "transaction_type", "customer_key"]
  )
}}

with sales as (
    select * from {{ ref('stg_online_retail') }}
)

select
    invoice_no,                                                    -- degenerate dimension

    cast(format_date('%Y%m%d', invoice_date) as int64)     as date_key,
    {{ dbt_utils.generate_surrogate_key(['stock_code']) }} as product_key,
    case
        when customer_id is null then 'UNKNOWN'
        else {{ dbt_utils.generate_surrogate_key(['customer_id']) }}
    end                                                    as customer_key,

    invoice_date,
    transaction_type,

    quantity,
    unit_price,
    revenue
from sales
