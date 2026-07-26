-- Wide "one big table" for BI: fact joined with all dimension attributes.
-- Looker connects here for KPIs, revenue trends, top products, geography.

select
    f.invoice_no,
    f.invoice_date,
    d.year, d.month, d.month_name, d.day_name, d.is_weekend,
    p.stock_code, p.description,
    c.customer_id, c.country,
    f.customer_key,
    f.transaction_type,
    f.quantity,
    f.unit_price,
    f.revenue
from {{ ref('fct_sales') }} f
join {{ ref('dim_date') }}     d on f.date_key     = d.date_key
join {{ ref('dim_product') }}  p on f.product_key  = p.product_key
join {{ ref('dim_customer') }} c on f.customer_key = c.customer_key
