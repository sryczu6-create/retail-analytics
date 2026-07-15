# Retail Sales Analytics — End-to-End Data Pipeline

> An end-to-end analytics project on the [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) dataset: from raw transactional data to a dimensional data warehouse, orchestrated ETL, advanced SQL analysis, and an interactive BI dashboard — ending in concrete business recommendations.

**Author:** SRY YULIANTI LOBO
📧 sryczu6@gmail.com · 🐙 [GitHub](https://github.com/sryczu6-create)
**Live dashboard:** [View on Looker Studio](https://datastudio.google.com/reporting/6e9af8d9-ecdb-4644-8946-d8044013c349)
**Tech stack:** PostgreSQL · Python (pandas, SQLAlchemy) · SQL (window functions, CTEs) · Looker Studio

![Dashboard](dashboard.png)

---

## 1. Project Overview

This project simulates the full workflow of a data analyst / data engineer working with retail transaction data. Starting from a raw, messy Excel file of ~1 million transactions, it builds a clean **star-schema data warehouse** in PostgreSQL, loads it through a modular **ETL pipeline**, runs **advanced SQL analyses** (RFM segmentation, cohort retention, month-over-month growth), and surfaces the results in an **interactive dashboard** with actionable business insights.

**Goals demonstrated:**
- Relational & dimensional database design (star schema, surrogate keys, referential integrity)
- ETL: extract, clean, classify, transform, and load with idempotency
- Complex SQL: window functions, CTEs, cohort analysis, customer segmentation
- BI dashboarding and data storytelling
- Translating numbers into business recommendations ("so what?")

---

## 2. Dataset

**Online Retail II** (UCI Machine Learning Repository) — real transactions from a UK-based online gift/homeware retailer, Dec 2009 – Dec 2011.

| Property | Value |
|---|---|
| Raw rows | ~1,067,000 |
| Rows after cleaning | ~1,033,000 |
| Columns | Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country |
| Time span | Dec 2009 – Dec 2011 |

**Why this dataset?** It is deliberately raw — a single flat table with real data-quality issues (cancellations, adjustments, negative quantities, ~25% missing customer IDs, duplicates). This required designing the dimensional model from scratch and handling messy data properly, rather than using a pre-cleaned dataset.

---

## 3. Architecture

```
Raw Excel (2 sheets)
      │
      ▼
[ extract.py ]  read + merge sheets
      │
      ▼
[ transform.py ]  clean, classify transaction_type, compute revenue
      │
      ▼
[ build_dimensions.py ]  dim_date · dim_product · dim_customer
[ build_fact.py ]        surrogate-key lookup → fact_sales
      │
      ▼
[ load.py ]  truncate + load (dimensions first, fact last)
      │
      ▼
PostgreSQL (star schema)  ──►  SQL analysis  ──►  Looker Studio dashboard
```

### Star schema

```
                 dim_date
                    │
dim_product ──── fact_sales ──── dim_customer
                    │
      measures: quantity, unit_price, revenue
      degenerate dim: invoice_no
      flag: transaction_type
```

**Design decisions (and why):**
- **Grain:** one row per invoice line item — the finest grain in the source, enabling aggregation to invoice / product / customer level without losing detail.
- **Star (not fully normalized):** OLAP workloads are read-heavy; star schema trades storage redundancy for fewer joins and faster aggregation.
- **Surrogate keys** in dimensions: decouple the warehouse from source-system changes and speed up integer joins.
- **Unknown member (`customer_key = -1`):** ~25% of transactions have no customer ID (guest checkout). Routing them to an unknown member keeps revenue totals correct and avoids NULL foreign keys, while customer-level analyses explicitly exclude it.
- **`NUMERIC` for money, not `FLOAT`:** avoids floating-point rounding errors when summing millions of rows.

---

## 4. Data Quality Handling

Rather than dropping messy rows, every row is **classified** so downstream queries can choose what to include. This keeps the pipeline auditable.

| transaction_type | Rule | In net revenue? |
|---|---|---|
| `SALE` | Normal sale | ✅ |
| `SHIPPING` | Postage/carriage codes (POST, DOT) | ✅ |
| `CANCELLATION` | Invoice starts with `C` (customer return) | ✅ (negative) |
| `ADJUSTMENT` | Invoice starts with `A`, or accounting codes | ❌ excluded |
| `WRITE_OFF` | Negative quantity, not a cancellation | ❌ excluded |

**Net Revenue** is defined as `SALE + SHIPPING + CANCELLATION`, excluding internal accounting adjustments and write-offs.

---

## 5. Key Analyses & Insights

All queries are in [`/sql`](./sql). Highlights:

### Month-over-Month Revenue Trend
Clear, repeating **seasonality**: revenue peaks in Sep–Nov (pre-holiday), troughs in Dec–Feb, in **both** 2010 and 2011.
> **Recommendation:** scale inventory up ahead of Sep–Nov; concentrate promotions in the Dec–Feb lull.
> *Note: Dec 2011 is truncated (data ends 9 Dec), so its apparent drop is a data artifact, not a real trend.*

### RFM Customer Segmentation
Customers scored on Recency, Frequency, Monetary and grouped into segments.
- **Champions (~22% of customers) drive ~68% of revenue** — a strong Pareto effect.
- **At-Risk** segment (~£1M revenue) = previously high-value customers who are lapsing.
> **Recommendation:** prioritize win-back campaigns for At-Risk customers — retention is cheaper than acquisition, and the value at stake is high.

### Cohort Retention
- Retention drops from 100% to **~35% in month 1** — 65% of customers do not return after their first purchase ("leaky bucket").
- Customers who survive month 1 stay relatively loyal (30–50%).
> **Recommendation:** launch a targeted "second purchase" campaign (time-limited discount 3–7 days after first order) — month-1 is the highest-leverage point.

### Top Products
Two profiles among best-sellers: high-margin **hero products** (Regency Cakestand) vs high-volume **traffic drivers** (T-Light Holder). Different stocking/promotion strategies apply to each.

---

## 6. Dashboard

Interactive dashboard built in **Looker Studio**: KPI cards (Net Revenue, Customers, Return Rate, AOV), monthly revenue trend, top products, RFM segments, and cohort retention.

🔗 **[View live dashboard](https://datastudio.google.com/reporting/6e9af8d9-ecdb-4644-8946-d8044013c349)**

| KPI | Value |
|---|---|
| Net Revenue | £19.3M |
| Total Customers | 5,955 |
| Return Rate | 5.9% |
| Avg Order Value | £479 |

---

## 7. Repository Structure

```
retail-analytics/
├── data/
│   ├── raw/              # source Excel (not tracked)
│   └── exports/          # query results as CSV for the dashboard
├── sql/
│   ├── 01_create_schema.sql
│   ├── 02_mom_growth.sql
│   ├── 03_rfm_segmentation.sql
│   └── 04_cohort_retention.sql
├── etl/
│   ├── config.py            # DB connection (reads .env)
│   ├── extract.py
│   ├── transform.py
│   ├── build_dimensions.py
│   ├── build_fact.py
│   └── load.py              # runs the full pipeline
├── dashboard.png
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 8. How to Run

```bash
# 1. Clone and enter the project
git clone https://github.com/sryczu6-create/retail-analytics.git
cd retail-analytics

# 2. Create environment and install dependencies
conda create -n retail python=3.11 -y
conda activate retail
pip install -r requirements.txt

# 3. Add your database URL to a .env file
echo "DATABASE_URL=postgresql://user:pass@host/db?sslmode=require" > .env

# 4. Create the schema (run sql/01_create_schema.sql on your database)

# 5. Run the full ETL pipeline
python etl/load.py
```

Download the dataset from [UCI](https://archive.ics.uci.edu/dataset/502/online+retail+ii) and place `online_retail_II.xlsx` in `data/raw/`.

---

## 9. Known Limitations

- **Truncated months:** data starts 1 Dec 2009 and ends 9 Dec 2011, so Dec 2009 and Dec 2011 are partial. Year-over-year comparisons account for this.
- **Write-offs recorded at price 0**, so inventory-loss value cannot be derived from this dataset.
- **~25% guest transactions** (no customer ID) are included in revenue totals but excluded from customer-level analysis.
- **Benchmark caveat:** external return-rate benchmarks (e.g. ~17.5% for UK e-commerce, *Loop 2025*) are not directly comparable due to differing methodology (order-based vs revenue-based), business model, and era; internal year-over-year comparison is used instead.

---

## 10. Skills Demonstrated

`PostgreSQL` · `Dimensional Modeling` · `Star Schema` · `ETL` · `Python` · `pandas` · `SQLAlchemy` · `SQL Window Functions` · `CTEs` · `RFM Analysis` · `Cohort Analysis` · `Looker Studio` · `Data Storytelling`
