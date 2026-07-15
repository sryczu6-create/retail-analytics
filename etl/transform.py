"""
transform.py — membersihkan & mengklasifikasikan data mentah.
Semua aturan di sini lahir dari profiling di Tahap 1.
"""
import pandas as pd


def classify_transaction(invoice: str, stock: str, qty: float) -> str:
    """
    Klasifikasi tiap baris ke 5 tipe.
    URUTAN PENTING: cek yang paling spesifik dulu (prioritas).
    """
    invoice = str(invoice)
    stock = str(stock).upper()

    # 1. ADJUSTMENT — invoice 'A' (bad debt) atau kode biaya khusus
    if invoice.startswith('A') or stock in ('B', 'BANK CHARGES', 'AMAZONFEE'):
        return 'ADJUSTMENT'
    # 2. CANCELLATION — invoice diawali 'C'
    if invoice.startswith('C'):
        return 'CANCELLATION'
    # 3. WRITE_OFF — qty negatif tapi bukan cancellation
    if qty < 0:
        return 'WRITE_OFF'
    # 4. SHIPPING — ongkir & sejenisnya (revenue, tapi bukan produk)
    if stock in ('POST', 'DOT', 'C2'):
        return 'SHIPPING'
    # 5. SALE — sisanya
    return 'SALE'


def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- Standarisasi nama kolom (spasi & huruf besar merepotkan di SQL) ---
    df = df.rename(columns={
        'Invoice': 'invoice_no',
        'StockCode': 'stock_code',
        'Description': 'description',
        'Quantity': 'quantity',
        'InvoiceDate': 'invoice_date',
        'Price': 'unit_price',
        'Customer ID': 'customer_id',
        'Country': 'country',
    })

    # --- Buang duplikat penuh ---
    before = len(df)
    df = df.drop_duplicates()
    print(f"  Duplikat dibuang: {before - len(df):,} baris")

    # --- Klasifikasi transaksi (vektorisasi lewat apply) ---
    df['transaction_type'] = df.apply(
        lambda r: classify_transaction(r['invoice_no'], r['stock_code'], r['quantity']),
        axis=1
    )

    # --- customer_id: float(17850.0) -> '17850', NaN -> None ---
    df['customer_id'] = df['customer_id'].apply(
        lambda x: str(int(x)) if pd.notna(x) else None
    )

    # --- Revenue (measure) ---
    df['revenue'] = (df['quantity'] * df['unit_price']).round(2)

    # --- Bersihkan description ---
    df['description'] = df['description'].astype(str).str.strip()
    df.loc[df['description'].isin(['', 'nan', 'None']), 'description'] = None

    return df


if __name__ == "__main__":
    from extract import extract
    df = extract()
    df = transform(df)

    print(f"\nTotal baris setelah transform: {len(df):,}")
    print("\nDistribusi transaction_type:")
    print(df['transaction_type'].value_counts())
    print("\nContoh data:")
    print(df[['invoice_no','stock_code','quantity','unit_price','revenue','transaction_type']].head())