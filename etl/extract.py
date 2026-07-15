"""
extract.py — membaca data mentah dari Excel (2 sheet) dan menggabungkannya.
"""
import pandas as pd

RAW_PATH = "data/raw/online_retail_II.xlsx"


def extract() -> pd.DataFrame:
    """Baca kedua sheet, gabungkan jadi satu DataFrame."""
    print("Membaca sheet 2009-2010...")
    df1 = pd.read_excel(RAW_PATH, sheet_name="Year 2009-2010")

    print("Membaca sheet 2010-2011...")
    df2 = pd.read_excel(RAW_PATH, sheet_name="Year 2010-2011")

    # Gabung dua sheet secara vertikal (baris ditumpuk)
    df = pd.concat([df1, df2], ignore_index=True)

    print(f"Total baris gabungan: {len(df):,}")
    return df


if __name__ == "__main__":
    df = extract()
    print(df.head())
    print("\nKolom:", list(df.columns))