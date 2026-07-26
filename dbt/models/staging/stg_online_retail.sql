-- Staging: clean & type the raw rows, classify each line's transaction_type,
-- and compute line-level revenue. One row per invoice line (source grain kept).
-- No joins or aggregation here — that belongs in the marts layer.

with source as (
    select * from {{ source('raw', 'online_retail_raw') }}
),

cleaned as (
    select
        cast(Invoice      as string)  as invoice_no,
        cast(StockCode    as string)  as stock_code,
        trim(Description)             as description,
        cast(Quantity     as int64)   as quantity,
        InvoiceDate                   as invoice_ts,
        date(InvoiceDate)             as invoice_date,
        cast(Price        as numeric) as unit_price,          -- NUMERIC for money (no float errors)
        cast(Customer_ID  as int64)   as customer_id,         -- NULL stays NULL (guest checkout)
        trim(Country)                as country,
        source_sheet
    from source
),

classified as (
    select
        *,
        round(quantity * unit_price, 2) as revenue,
        case
            when upper(invoice_no) like 'C%'        then 'CANCELLATION'  -- customer return
            when upper(invoice_no) like 'A%'        then 'ADJUSTMENT'    -- accounting adjustment
            when stock_code in ('POST', 'DOT', 'C2') then 'SHIPPING'     -- postage/carriage
            when quantity < 0                        then 'WRITE_OFF'    -- negative qty, not a cancellation
            else 'SALE'
        end as transaction_type
    from cleaned
)

select * from classified
