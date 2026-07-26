-- Customer dimension: one row per customer_id (+ most frequent country),
-- plus an explicit UNKNOWN member for guest checkouts (source customer_id NULL).
-- Mirrors the original star schema's unknown member (customer_key = -1):
-- keeps revenue totals correct and avoids NULL foreign keys in the fact.

with ranked as (
    select
        customer_id,
        country,
        row_number() over (partition by customer_id order by count(*) desc) as rn
    from {{ ref('stg_online_retail') }}
    where customer_id is not null
    group by customer_id, country
)

select
    {{ dbt_utils.generate_surrogate_key(['customer_id']) }} as customer_key,
    customer_id,
    country
from ranked
where rn = 1

union all

select
    'UNKNOWN' as customer_key,
    null      as customer_id,
    'Unknown' as country
