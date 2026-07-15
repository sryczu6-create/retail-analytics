-- ============================================================
-- Analisis: Month-over-Month (MoM) Revenue Growth
-- Teknik: CTE + window function (LAG)
--
-- INSIGHT:
-- - Pola musiman jelas & BERULANG di 2010 dan 2011:
--   penjualan naik Sep-Nov (puncak November ~1.43jt, jelang
--   musim liburan), lalu turun Des-Feb.
-- - Actionable: perbanyak stok jelang Sep-Nov; fokuskan
--   promosi/diskon di masa sepi Des-Feb.
-- - CATATAN DATA: Desember 2011 terpotong (data berhenti
--   9 Des 2011), sehingga penurunan tajam Desember adalah
--   ARTEFAK data, bukan tren bisnis nyata. Dikecualikan dari
--   interpretasi tren.
-- ============================================================

WITH revenue_per_bulan AS (
    SELECT
        d.year,
        d.month,
        SUM(f.revenue) AS revenue
    FROM fact_sales f
    JOIN dim_date d ON f.date_key = d.date_key
    WHERE f.transaction_type = 'SALE'
    GROUP BY d.year, d.month
)
SELECT
    -- kolom baru: label waktu berurutan, mis. "2010-01"
    year || '-' || LPAD(month::text, 2, '0') AS year_month,
    year,
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY year, month) AS revenue_bulan_lalu,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY year, month))
        * 100.0
        / LAG(revenue) OVER (ORDER BY year, month), 2
    ) AS mom_growth_pct
FROM revenue_per_bulan
ORDER BY year, month;