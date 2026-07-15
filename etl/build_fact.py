"""
build_fact.py — membangun fact_sales dengan menerjemahkan natural key
(stock_code, customer_id, tanggal) menjadi surrogate key (product_key,
customer_key, date_key) lewat lookup ke tabel dimensi.
"""
import pandas as pd


def build_fact(df: pd.DataFrame, dim_product: pd.DataFrame,
               dim_customer: pd.DataFrame) -> pd.DataFrame:
    fact = df.copy()

    # --- date_key: dari invoice_date -> YYYYMMDD ---
    fact['date_key'] = fact['invoice_date'].dt.strftime('%Y%m%d').astype(int)

    # --- product_key: lookup stock_code -> product_key ---
    # Buat "kamus" penerjemah dari dim_product
    product_map = dim_product.set_index('stock_code')['product_key']
    fact['product_key'] = fact['stock_code'].map(product_map)

    # --- customer_key: lookup (customer_id, country) -> customer_key ---
    # Kunci gabungan karena dim_customer unik per (customer_id, country)
    cust_map = dim_customer.set_index(['customer_id', 'country'])['customer_key']
    # Untuk baris tanpa customer_id, arahkan ke unknown member (-1)
    def lookup_customer(row):
        if pd.isna(row['customer_id']):
            return -1
        return cust_map.get((row['customer_id'], row['country']), -1)
    fact['customer_key'] = fact.apply(lookup_customer, axis=1)

    # --- Pilih hanya kolom yang masuk ke tabel fact_sales ---
    fact = fact[[
        'date_key', 'product_key', 'customer_key',
        'invoice_no', 'quantity', 'unit_price', 'revenue', 'transaction_type'
    ]]

    # --- Sanity check: tidak boleh ada key yang gagal lookup (NaN) ---
    missing_product = fact['product_key'].isna().sum()
    missing_customer = fact['customer_key'].isna().sum()
    print(f"  product_key gagal lookup: {missing_product}")
    print(f"  customer_key gagal lookup: {missing_customer}")

    print(f"  fact_sales siap: {len(fact):,} baris")
    return fact


if __name__ == "__main__":
    from extract import extract
    from transform import transform
    from build_dimensions import build_dim_product, build_dim_customer

    df = transform(extract())
    dim_product = build_dim_product(df)
    dim_customer = build_dim_customer(df)

    print("\nMembangun fact_sales:")
    fact = build_fact(df, dim_product, dim_customer)

    print("\nContoh fact_sales:")
    print(fact.head().to_string())