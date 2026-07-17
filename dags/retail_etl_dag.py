"""
retail_etl_dag.py — Airflow DAG untuk pipeline Retail Sales Analytics.

Memecah ETL menjadi task terpisah (extract -> transform -> build dims ->
build fact -> load) dengan staging parquet antar-task, sehingga:
  - kegagalan bisa di-retry per-task (tidak mengulang dari awal)
  - urutan dependency dijamin (fact menunggu dimensi)
  - idempotent: aman dijalankan ulang
"""
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator

# --- Path ---
# Sesuaikan BASE_DIR dengan lokasi proyek di lingkungan Airflow-mu.
BASE_DIR = Path("/mnt/d/projects/retail-analytics")      # di dalam container/WSL
STAGING = BASE_DIR / "data" / "staging"

# Impor logika ETL yang sudah kamu tulis (dari folder etl/)
import sys
sys.path.append(str(BASE_DIR / "etl"))
from extract import extract
from transform import transform
from build_dimensions import build_dim_date, build_dim_product, build_dim_customer
from build_fact import build_fact
from config import engine


# ============================================================
# FUNGSI TIAP TASK
# Tiap task: baca input dari staging, proses, tulis output ke staging.
# Ini membuat task STATELESS — bisa retry independen.
# ============================================================

def task_extract(**context):
    df = extract()
    STAGING.mkdir(parents=True, exist_ok=True)
    df.to_parquet(STAGING / "raw.parquet")
    print(f"Extract selesai: {len(df):,} baris")


def task_transform(**context):
    df = pd.read_parquet(STAGING / "raw.parquet")
    df = transform(df)
    df.to_parquet(STAGING / "clean.parquet")
    print(f"Transform selesai: {len(df):,} baris")


def task_build_dimensions(**context):
    df = pd.read_parquet(STAGING / "clean.parquet")
    build_dim_date(df).to_parquet(STAGING / "dim_date.parquet")
    build_dim_product(df).to_parquet(STAGING / "dim_product.parquet")
    build_dim_customer(df).to_parquet(STAGING / "dim_customer.parquet")
    print("Dimensi selesai dibangun")


def task_build_fact(**context):
    df = pd.read_parquet(STAGING / "clean.parquet")
    dim_product = pd.read_parquet(STAGING / "dim_product.parquet")
    dim_customer = pd.read_parquet(STAGING / "dim_customer.parquet")
    fact = build_fact(df, dim_product, dim_customer)
    fact.to_parquet(STAGING / "fact_sales.parquet")
    print(f"Fact selesai: {len(fact):,} baris")


def task_load(**context):
    """Load ke Postgres pakai psycopg2 langsung (stabil, cepat, bebas versi)."""
    import psycopg2
    from psycopg2.extras import execute_values
    import os
    from dotenv import load_dotenv
    from pathlib import Path

    load_dotenv(Path("/mnt/d/projects/retail-analytics/.env"))
    dsn = os.getenv("DATABASE_URL")

    dim_date = pd.read_parquet(STAGING / "dim_date.parquet")
    dim_product = pd.read_parquet(STAGING / "dim_product.parquet")
    dim_customer = pd.read_parquet(STAGING / "dim_customer.parquet")
    fact = pd.read_parquet(STAGING / "fact_sales.parquet")

    def insert_df(cur, table, df):
        cols = list(df.columns)
        col_str = ",".join(cols)
        # ubah NaN jadi None supaya jadi NULL di SQL
        rows = [tuple(None if pd.isna(v) else v for v in row)
                for row in df.itertuples(index=False, name=None)]
        sql = f"INSERT INTO {table} ({col_str}) VALUES %s"
        execute_values(cur, sql, rows, page_size=5000)
        print(f"  {table}: {len(df):,} baris")

    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            # Idempotency
            cur.execute("TRUNCATE fact_sales, dim_product, dim_customer, dim_date "
                        "RESTART IDENTITY CASCADE;")
            # Urutan wajib: dimensi dulu, fact terakhir
            insert_df(cur, "dim_date", dim_date)
            insert_df(cur, "dim_product", dim_product)
            insert_df(cur, "dim_customer", dim_customer)
            insert_df(cur, "fact_sales", fact)
        conn.commit()
        print("Load ke PostgreSQL selesai")
    finally:
        conn.close()


def task_validate(**context):
    """Sanity check sederhana setelah load."""
    from sqlalchemy import text
    with engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM fact_sales")).scalar()
    print(f"Validasi: fact_sales berisi {n:,} baris")
    if n == 0:
        raise ValueError("fact_sales kosong — load gagal!")


# ============================================================
# DEFAULT ARGUMENTS — berlaku untuk semua task
# ============================================================
default_args = {
    "owner": "sry",
    "retries": 2,                          # coba ulang 2x jika gagal
    "retry_delay": timedelta(minutes=1),   # jeda antar percobaan
}

# ============================================================
# DEFINISI DAG
# ============================================================
with DAG(
    dag_id="retail_etl_pipeline",
    description="ETL Online Retail II -> star schema PostgreSQL",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="@daily",        # jadwal: sekali sehari (bisa None untuk manual)
    catchup=False,            # jangan backfill tanggal lampau
    tags=["retail", "etl", "portfolio"],
) as dag:

    extract_t = PythonOperator(task_id="extract", python_callable=task_extract)
    transform_t = PythonOperator(task_id="transform", python_callable=task_transform)
    dims_t = PythonOperator(task_id="build_dimensions", python_callable=task_build_dimensions)
    fact_t = PythonOperator(task_id="build_fact", python_callable=task_build_fact)
    load_t = PythonOperator(task_id="load", python_callable=task_load)
    validate_t = PythonOperator(task_id="validate", python_callable=task_validate)

    # ============================================================
    # DEPENDENCIES — inilah "bentuk" pipeline-nya
    # ============================================================
    extract_t >> transform_t >> dims_t >> fact_t >> load_t >> validate_t
