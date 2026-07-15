-- ============================================================
-- Analisis: Cohort Retention Analysis
-- Teknik: CTE bertingkat + window function (FIRST_VALUE, PARTITION BY)
--
-- INSIGHT:
-- - "Leaky bucket": retention terjun dari 100% (Bulan-0) ke ~35%
--   (Bulan-1). 65% pelanggan TIDAK kembali setelah pembelian pertama.
--   -> Titik ungkit tertinggi = konversi pembelian ke-2.
-- - Setelah terjun awal, retention stabil di 30-50% -> ada inti
--   pelanggan loyal. Masalah bukan produk, tapi aktivasi pembeli baru.
-- - Puncak retention Bulan-11 (~50%) jatuh di Nov 2010 -> konsisten
--   dengan pola musiman di analisis MoM (saling menguatkan).
-- - Rekomendasi: kampanye "second purchase" (kupon diskon berbatas
--   waktu, dikirim 3-7 hari setelah order pertama).
-- ============================================================

WITH first_purchase AS (
    SELECT
        f.customer_key,
        DATE_TRUNC('month', MIN(d.full_date))::date AS cohort_month
    FROM fact_sales f
    JOIN dim_date d ON f.date_key = d.date_key
    WHERE f.transaction_type = 'SALE'
      AND f.customer_key <> -1
    GROUP BY f.customer_key
),
activity AS (
    SELECT
        f.customer_key,
        fp.cohort_month,
        (EXTRACT(YEAR  FROM d.full_date) - EXTRACT(YEAR  FROM fp.cohort_month)) * 12
      + (EXTRACT(MONTH FROM d.full_date) - EXTRACT(MONTH FROM fp.cohort_month))
            AS month_number
    FROM fact_sales f
    JOIN dim_date d        ON f.date_key = d.date_key
    JOIN first_purchase fp ON f.customer_key = fp.customer_key
    WHERE f.transaction_type = 'SALE'
      AND f.customer_key <> -1
),
cohort_counts AS (
    SELECT
        cohort_month,
        month_number,
        COUNT(DISTINCT customer_key) AS jumlah_aktif
    FROM activity
    GROUP BY cohort_month, month_number
)
SELECT
    cohort_month,
    month_number,
    jumlah_aktif,
    FIRST_VALUE(jumlah_aktif) OVER (
        PARTITION BY cohort_month ORDER BY month_number
    ) AS ukuran_cohort,
    ROUND(
        jumlah_aktif * 100.0 /
        FIRST_VALUE(jumlah_aktif) OVER (
            PARTITION BY cohort_month ORDER BY month_number
        ), 1
    ) AS retention_pct
FROM cohort_counts
ORDER BY cohort_month, month_number;