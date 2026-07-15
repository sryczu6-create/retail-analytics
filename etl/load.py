"""
load.py — orkestrasi penuh: extract -> transform -> build -> load ke Neon.
Menjalankan file ini = menjalankan seluruh pipeline ETL.
"""
from sqlalchemy import text

from config import engine
from extract import extract
from transform import transform
from build_dimensions import build_dim_date, build_dim_product, build_dim_customer
from build_fact import build_fact


def truncate_all():
    """
    Kosongkan semua tabel sebelum load ulang (idempotency).
    Urutan: fact dulu (karena punya FK ke dimensi), baru dimensi.
    RESTART IDENTITY mereset counter surrogate key.
    """
    with engine.begin() as conn:
        conn.execute(text("""
            TRUNCATE fact_sales, dim_product, dim_customer, dim_date
            RESTART IDENTITY CASCADE;
        """))
    print("  Semua tabel dikosongkan.")


def load_table(df, table_name, include_index=False):
    """Muat satu DataFrame ke tabel Postgres."""
    df.to_sql(table_name, engine, if_exists='append',
              index=include_index, method='multi', chunksize=5000)
    print(f"  {table_name}: {len(df):,} baris dimuat.")


def run_pipeline():
    print("=== EXTRACT ===")
    df = extract()

    print("=== TRANSFORM ===")
    df = transform(df)

    print("=== BUILD DIMENSIONS ===")
    dim_date = build_dim_date(df)
    dim_product = build_dim_product(df)
    dim_customer = build_dim_customer(df)

    print("=== BUILD FACT ===")
    fact = build_fact(df, dim_product, dim_customer)

    print("=== LOAD (urutan: dimensi dulu, fact terakhir) ===")
    truncate_all()
    load_table(dim_date, 'dim_date')
    load_table(dim_product, 'dim_product')
    load_table(dim_customer, 'dim_customer')
    load_table(fact, 'fact_sales')

    print("\n=== PIPELINE SELESAI ===")


if __name__ == "__main__":
    run_pipeline()