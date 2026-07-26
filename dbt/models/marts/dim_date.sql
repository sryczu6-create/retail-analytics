-- Date dimension: one row per calendar day spanning the data.
-- Built with GENERATE_DATE_ARRAY — no source table needed.

with dates as (
    select d as full_date
    from unnest(generate_date_array('2009-12-01', '2011-12-31')) as d
)

select
    cast(format_date('%Y%m%d', full_date) as int64) as date_key,   -- surrogate key YYYYMMDD
    full_date,
    extract(year      from full_date) as year,
    extract(quarter   from full_date) as quarter,
    extract(month     from full_date) as month,
    format_date('%B', full_date)      as month_name,
    extract(day       from full_date) as day_of_month,
    format_date('%A', full_date)      as day_name,
    extract(dayofweek from full_date) in (1, 7) as is_weekend      -- 1=Sun, 7=Sat
from dates
