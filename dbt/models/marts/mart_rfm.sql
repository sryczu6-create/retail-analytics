-- RFM customer segmentation (ported from sql/03_rfm_segmentation.sql).
-- Technique: nested CTEs + NTILE(5) scoring + CASE segmentation.
-- Guest checkouts (customer_key = 'UNKNOWN') are excluded (untraceable).

with rfm_raw as (
    select
        customer_key,
        date_diff(date '2011-12-10', max(invoice_date), day) as recency_days,
        count(distinct invoice_no)                           as frequency,
        sum(revenue)                                         as monetary
    from {{ ref('fct_sales') }}
    where transaction_type = 'SALE'
      and customer_key <> 'UNKNOWN'
    group by customer_key
),

rfm_scored as (
    select
        *,
        ntile(5) over (order by recency_days desc) as r_score,
        ntile(5) over (order by frequency)         as f_score,
        ntile(5) over (order by monetary)          as m_score
    from rfm_raw
)

select
    customer_key,
    recency_days,
    frequency,
    monetary,
    r_score, f_score, m_score,
    case
        when r_score >= 4 and f_score >= 4 and m_score >= 4 then 'Champions'
        when r_score >= 3 and f_score >= 3                  then 'Loyal'
        when r_score >= 4 and f_score <= 2                  then 'New/Promising'
        when r_score <= 2 and f_score >= 4 and m_score >= 4 then 'At-Risk'
        when r_score <= 2 and f_score <= 2                  then 'Lost'
        else 'Others'
    end as segment
from rfm_scored
