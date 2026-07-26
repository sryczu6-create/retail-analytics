-- Product dimension: one row per stock_code, with the most frequent
-- non-null description (the source has the same code with varied text).

with ranked as (
    select
        stock_code,
        description,
        row_number() over (partition by stock_code order by count(*) desc, description) as rn
    from {{ ref('stg_online_retail') }}
    where stock_code is not null
    group by stock_code, description
)

select
    {{ dbt_utils.generate_surrogate_key(['stock_code']) }} as product_key,
    stock_code,
    description
from ranked
where rn = 1
