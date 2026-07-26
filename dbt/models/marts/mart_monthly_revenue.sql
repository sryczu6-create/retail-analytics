-- Month-over-month revenue growth (ported from sql/02_mom_growth.sql).
-- Technique: monthly aggregation + LAG window function.

with revenue_per_month as (
    select
        date_trunc(invoice_date, month) as month_start,
        sum(revenue) as revenue
    from {{ ref('fct_sales') }}
    where transaction_type = 'SALE'
    group by 1
)

select
    format_date('%Y-%m', month_start) as year_month,
    extract(year  from month_start)   as year,
    extract(month from month_start)   as month,
    revenue,
    lag(revenue) over (order by month_start) as prev_month_revenue,
    round(
        safe_divide(
            revenue - lag(revenue) over (order by month_start),
            lag(revenue) over (order by month_start)
        ) * 100, 2
    ) as mom_growth_pct
from revenue_per_month
order by month_start
