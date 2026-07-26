-- Singular test: the fact must keep exactly the staging grain (no rows
-- dropped or duplicated by the transformation). Returns rows only on failure.
with fact    as (select count(*) as n from {{ ref('fct_sales') }}),
     staging as (select count(*) as n from {{ ref('stg_online_retail') }})
select f.n as fact_rows, s.n as staging_rows
from fact f cross join staging s
where f.n <> s.n
