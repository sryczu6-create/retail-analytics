"""
build_dimensions.py — membangun dim_date, dim_product, dim_customer
dari data yang sudah di-transform.
"""
import pandas as pd


# ============================================================
# BAGIAN 1: dim_date — generate kalender dari rentang tanggal data
# ============================================================
def build_dim_date(df: pd.DataFrame) -> pd.DataFrame:
    # Ambil tanggal min & max dari data (buang jam, ambil tanggalnya saja)
    min_date = df['invoice_date'].min().normalize()
    max_date = df['invoice_date'].max().normalize()

    # Buat satu baris untuk SETIAP hari dalam rentang (termasuk hari tanpa transaksi)
    dates = pd.date_range(start=min_date, end=max_date, freq='D')

    dim = pd.DataFrame({'full_date': dates})
    dim['date_key']     = dim['full_date'].dt.strftime('%Y%m%d').astype(int)  # 20101201
    dim['year']         = dim['full_date'].dt.year
    dim['quarter']      = dim['full_date'].dt.quarter
    dim['month']        = dim['full_date'].dt.month
    dim['month_name']   = dim['full_date'].dt.strftime('%B')      # 'December'
    dim['day_of_month'] = dim['full_date'].dt.day
    dim['day_of_week']  = dim['full_date'].dt.dayofweek + 1        # 0=Senin -> 1=Senin
    dim['day_name']     = dim['full_date'].dt.strftime('%A')      # 'Wednesday'
    dim['is_weekend']   = dim['day_of_week'].isin([6, 7])          # Sabtu/Minggu
    dim['week_of_year'] = dim['full_date'].dt.isocalendar().week.astype(int)

    # full_date harus bertipe date (bukan datetime) untuk cocok dengan skema
    dim['full_date'] = dim['full_date'].dt.date

    print(f"  dim_date: {len(dim):,} baris ({min_date.date()} s/d {max_date.date()})")
    return dim


# ============================================================
# BAGIAN 2: dim_product — produk unik + surrogate key + flag is_product
# ============================================================
def build_dim_product(df: pd.DataFrame) -> pd.DataFrame:
    # Ambil kombinasi stock_code unik. Untuk description, ambil yang paling sering muncul
    # (satu stock_code kadang punya beberapa variasi deskripsi; kita pilih modus)
    prod = (
        df.groupby('stock_code')['description']
        .agg(lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else None)
        .reset_index()
    )

    # Flag: apakah ini produk sungguhan, atau biaya/ongkir/adjustment?
    non_product = {'POST', 'DOT', 'C2', 'M', 'B', 'D', 'S',
                   'BANK CHARGES', 'AMAZONFEE', 'CRUK', 'PADS', 'GIFT'}
    prod['is_product'] = ~prod['stock_code'].astype(str).str.upper().isin(non_product)

    prod['category'] = None  # diisi nanti (Tahap categorization)

    # Surrogate key: 1, 2, 3, ... (product_key)
    prod = prod.reset_index(drop=True)
    prod['product_key'] = prod.index + 1

    prod = prod.rename(columns={'description': 'description'})
    prod = prod[['product_key', 'stock_code', 'description', 'category', 'is_product']]

    print(f"  dim_product: {len(prod):,} produk unik "
          f"({(~prod['is_product']).sum()} ditandai non-produk)")
    return prod


# ============================================================
# BAGIAN 3: dim_customer — pelanggan unik + unknown member (-1)
# ============================================================
def build_dim_customer(df: pd.DataFrame) -> pd.DataFrame:
    # Ambil kombinasi (customer_id, country) unik, hanya yang customer_id-nya ADA
    known = (
        df[df['customer_id'].notna()][['customer_id', 'country']]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    known['customer_key'] = known.index + 1   # surrogate key mulai dari 1

    # Baris unknown member (-1) untuk transaksi tanpa customer_id
    unknown = pd.DataFrame([{
        'customer_key': -1,
        'customer_id': 'UNKNOWN',
        'country': 'Unknown'
    }])

    dim = pd.concat([unknown, known], ignore_index=True)
    dim = dim[['customer_key', 'customer_id', 'country']]

    print(f"  dim_customer: {len(dim):,} baris (termasuk 1 unknown member)")
    return dim


if __name__ == "__main__":
    from extract import extract
    from transform import transform

    df = transform(extract())

    print("\nMembangun dimensi:")
    dim_date = build_dim_date(df)
    dim_product = build_dim_product(df)
    dim_customer = build_dim_customer(df)

    print("\nContoh dim_date:")
    print(dim_date.head(3).to_string())
    print("\nContoh dim_product:")
    print(dim_product.head(3).to_string())
    print("\nContoh dim_customer:")
    print(dim_customer.head(3).to_string())