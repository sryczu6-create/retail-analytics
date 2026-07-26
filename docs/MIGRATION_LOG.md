# Cloud Migration Log

Migrating the Retail Sales Analytics project from a local PostgreSQL star schema
to a cloud-native stack: **BigQuery + dbt + Airflow + GitHub Actions CI + Looker Studio**.

The goal is to keep all existing business logic (dimensional model, `transaction_type`
classification, RFM/cohort/MoM analyses) and change only *where* data lives and *how*
transformations are built, tested, and orchestrated.

---

## Stage 1 — GCP setup & cost safety

**Objective:** stand up a cloud data warehouse with a hard guarantee of zero cost.

**Decisions & rationale:**
- **BigQuery Sandbox (no billing account, no credit card).** With no payment method
  attached to the project, there is no channel through which charges can occur — a
  stronger guarantee than budget alerts. Trade-off: 60-day table expiration, no
  streaming inserts, some enterprise features locked — none of which affect this project.
- **Free-tier headroom:** raw dataset is ~45 MB (~1.3% of the 10 GB storage allowance);
  1 TB/month query allowance is far beyond this workload.
- **Local auth via `gcloud` OAuth (planned), not service-account key files.** Avoids
  long-lived secrets that could leak to GitHub — the most common cause of cloud breaches.
  Service-account keys reserved for CI only, stored in GitHub Secrets.
- **Environment:** WSL2 (Ubuntu) to mirror a Linux production runtime. Isolated
  Python 3.12 via `uv` because `dbt-bigquery` did not yet support the system Python 3.14.
- **Repo hygiene:** added `.gitignore` covering `.env`, service-account JSON keys,
  dbt build artifacts, and large data files *before* creating any credentials.

**Project ID:** \`tokyo-epoch-226208\`

---

## Stage 2 — Ingest raw data into BigQuery

**Objective:** land the ~1M source rows in a `raw` layer, faithful to source.

**What was done:**
- Unioned the two yearly Excel sheets (525,461 + 541,910 = **1,067,371 rows**).
- Converted `.xlsx` -> **Parquet** locally: 45 MB -> **7.2 MB**, types preserved
  (dates as datetime, numbers as numeric). Forced text columns to string to handle
  mixed Invoice codes (e.g. `C489449`). Added a `source_sheet` lineage column.
- Created dataset **`raw`** in the **US multi-region** (permanent; all datasets must match).
- Loaded with `bq load --source_format=PARQUET`; row count verified **1,067,371**
  in BigQuery = local count. `Customer_ID` null in 243,007 rows (~22.8%, guest checkout).

**Cost & safety:**
- Ingestion is free; storage ~7 MB = ~0.07% of the 10 GB free allowance.
- Auth via `gcloud` user OAuth — no service-account key files on disk.
- BigQuery is columnar: cost = bytes scanned. Use explicit column lists and
  `--dry_run` to estimate before running. Sandbox enforces 60-day table expiration.

---

## Stage 3 — dbt transformation layer (sources -> staging -> marts)

**Objective:** rebuild the star schema as a tested, dependency-aware dbt project on BigQuery.

**Why dbt over plain SQL scripts:** automatic dependency ordering via `ref()`, tests
and docs as first-class citizens, SELECT-only models (dbt manages DDL), and Git/CI-friendly
version control.

**Structure:**
- **Source:** `raw.online_retail_raw` declared in `_sources.yml`.
- **Staging (`stg_online_retail`, view):** clean & type columns, classify
  `transaction_type` (SALE / CANCELLATION / SHIPPING / WRITE_OFF / ADJUSTMENT),
  compute line revenue. Net revenue ~£19.4M — matches the original PostgreSQL build.
- **Dimensions (tables):** `dim_date` (761 days via GENERATE_DATE_ARRAY),
  `dim_product` (5,305; most-frequent description per stock_code),
  `dim_customer` (5,942 + explicit UNKNOWN member for guest checkouts).
  Surrogate keys via `dbt_utils.generate_surrogate_key` (deterministic hashes,
  stable across reloads — unlike sequential row numbers).
- **Fact (`fct_sales`, table):** 1,067,371 rows; FKs to all dims, degenerate
  dimension `invoice_no`, additive measures.

**Cost design & platform constraint:**
- Intended `partition_by=invoice_date`. Discovered the **BigQuery Sandbox enforces a
  60-day partition expiration** that cannot be disabled — it immediately empties
  partitions holding historical 2009-2011 dates (fact came back with 0 rows).
- Fix: **cluster** by `invoice_date, transaction_type, customer_key` (no expiration,
  still prunes date-range/segment scans). A billing-enabled project would partition
  by `invoice_date` with partition expiration disabled.
- Auth: dbt uses OAuth ADC — no service-account key files on disk.

---

## Stage 4 — Data quality tests & documentation

**Objective:** make the pipeline trustworthy and self-documenting.

**Tests (20 total, all passing):**
- **Generic:** `unique` + `not_null` on every dimension surrogate key (grain guard);
  `relationships` from all three fact FKs to their dimensions (referential integrity);
  `accepted_values` on `transaction_type` (controlled vocabulary).
- **Singular (custom):** `assert_fact_matches_staging_count` — fails if the fact grain
  drifts from staging (no rows dropped/duplicated).

**When to test (rationale):** guard the primary key/grain, referential integrity,
controlled vocabularies, and business invariants — not trivially-derived columns.
Use generic tests for reusable rules; singular tests only for project-specific invariants.

**Docs:** `dbt docs generate` produces an interactive catalog + a lineage graph
(raw -> staging -> dims/fact -> tests), used as a portfolio artifact.

**Note:** column-argument syntax uses the current dbt `arguments:` nesting (clean build,
no deprecation warnings) — important for the CI step.

---

## Stage 5 — Airflow orchestration to BigQuery

**Objective:** let Airflow orchestrate the dbt build/test against BigQuery
(replacing the old DAG's PostgreSQL load).

**DAG `retail_dbt_pipeline`:** `dbt_deps -> dbt_run -> dbt_test`, each a BashOperator
invoking the dbt 3.12 venv binary. Tasks are split for granular recovery (a failed
`test` re-runs only `test`) — the same principle as the original ETL DAG.

**Details:**
- Absolute paths + `export HOME` so dbt finds `~/.dbt/profiles.yml` and the gcloud ADC.
- DAG lives in the repo (`dags/`) and is symlinked into Airflow's dags folder
  (version-controlled, discoverable by Airflow).
- Executed headless with `airflow dags test` (no scheduler/webserver needed on WSL):
  DagRun state = **success** (deps OK, run PASS=5, test PASS=20).
