-- Cohort retention (ported from sql/04_cohort_retention.sql).
-- Technique: first-purchase cohort + month offset + FIRST_VALUE window.
-- Guest checkouts excluded.

with first_purchase as (
    select
        customer_key,
        date_trunc(min(invoice_date), month) as cohort_month
    from {{ ref('fct_sales') }}
    where transaction_type = 'SALE' and customer_key <> 'UNKNOWN'
    group by customer_key
),

activity as (
    select
        f.customer_key,
        fp.cohort_month,
        date_diff(date_trunc(f.invoice_date, month), fp.cohort_month, month) as month_number
    from {{ ref('fct_sales') }} f
    join first_purchase fp on f.customer_key = fp.customer_key
    where f.transaction_type = 'SALE' and f.customer_key <> 'UNKNOWN'
),

cohort_counts as (
    select cohort_month, month_number, count(distinct customer_key) as active_customers
    from activity
    group by cohort_month, month_number
)

select
    cohort_month,
    month_number,
    active_customers,
    first_value(active_customers) over (
        partition by cohort_month order by month_number
    ) as cohort_size,
    round(
        active_customers * 100.0 / first_value(active_customers) over (
            partition by cohort_month order by month_number
        ), 1
    ) as retention_pct
from cohort_counts
order by cohort_month, month_number
