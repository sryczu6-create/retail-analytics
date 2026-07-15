-- ============================================================
-- Analisis: RFM Customer Segmentation
-- Teknik: CTE bertingkat (3 level) + window function (NTILE) + CASE
--
-- INSIGHT:
-- - Pareto/80-20 nyata: segmen "Champions" (~22% pelanggan)
--   menyumbang ~68% total revenue. Ketergantungan tinggi pada
--   sedikit pelanggan bernilai besar.
-- - Segmen "At-Risk" (234 pelanggan, ~1jt revenue): pelanggan
--   dulu bernilai tinggi yang mulai menghilang -> prioritas
--   win-back karena biaya retensi < biaya akuisisi baru.
-- - Segmen "Lost" (1.522 pelanggan tapi hanya ~625rb revenue):
--   bernilai rendah sejak awal -> hanya layak kampanye murah/otomatis.
-- - CATATAN: unknown member (customer_key = -1 / guest ~25%)
--   DIKECUALIKAN karena tidak dapat dilacak per individu.
-- ============================================================

WITH rfm_raw AS (
    SELECT
        f.customer_key,
        (DATE '2011-12-10' - MAX(d.full_date))   AS recency_hari,
        COUNT(DISTINCT f.invoice_no)             AS frequency,
        SUM(f.revenue)                           AS monetary
    FROM fact_sales f
    JOIN dim_date d ON f.date_key = d.date_key
    WHERE f.transaction_type = 'SALE'
      AND f.customer_key <> -1
    GROUP BY f.customer_key
),
rfm_scored AS (
    SELECT
        customer_key, recency_hari, frequency, monetary,
        NTILE(5) OVER (ORDER BY recency_hari DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency)         AS f_score,
        NTILE(5) OVER (ORDER BY monetary)          AS m_score
    FROM rfm_raw
),
rfm_segmented AS (
    SELECT
        customer_key,
        monetary,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal'
            WHEN r_score >= 4 AND f_score <= 2                  THEN 'New/Promising'
            WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4 THEN 'At-Risk'
            WHEN r_score <= 2 AND f_score <= 2                  THEN 'Lost'
            ELSE 'Others'
        END AS segment
    FROM rfm_scored
)
SELECT
    segment,
    COUNT(DISTINCT customer_key) AS jumlah_pelanggan,
    SUM(monetary)                AS total_revenue
FROM rfm_segmented
GROUP BY segment
ORDER BY total_revenue DESC;