"""
Convert the raw Online Retail II Excel workbook (2 sheets) into a single
Parquet file, ready to load into the BigQuery `raw` layer.

Raw-layer philosophy: stay faithful to the source. We only
  - union the two yearly sheets into one table,
  - add a `source_sheet` lineage column,
  - make column names BigQuery-safe (spaces -> underscores),
  - force text-like columns to string so PyArrow can serialize the mixed
    numeric/letter Invoice codes (e.g. 'C489449' cancellations).
All cleaning, typing and business logic happen later in dbt (staging).
"""

from pathlib import Path
import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
SRC = RAW_DIR / "online_retail_II.xlsx"
OUT = RAW_DIR / "online_retail_raw.parquet"


def bq_safe(col: str) -> str:
    """Make a column name safe for BigQuery (letters, digits, underscores)."""
    return col.strip().replace(" ", "_")


def main() -> None:
    print(f"Reading {SRC} (this can take 1-2 minutes) ...")
    # sheet_name=None -> dict {sheet_name: DataFrame}, robust to sheet naming
    sheets = pd.read_excel(SRC, sheet_name=None, engine="openpyxl")
    print(f"Found sheets: {list(sheets)}")

    frames = []
    for name, df in sheets.items():
        df = df.copy()
        df["source_sheet"] = name
        frames.append(df)
        print(f"  {name}: {len(df):,} rows")

    data = pd.concat(frames, ignore_index=True)
    data.columns = [bq_safe(c) for c in data.columns]

    # Force mixed-type / text columns to string for clean Parquet serialization
    for col in ["Invoice", "StockCode", "Description", "Country", "source_sheet"]:
        if col in data.columns:
            data[col] = data[col].astype("string")

    print("\n=== RAW SUMMARY ===")
    print(f"Total rows : {len(data):,}")
    print(f"Columns    : {list(data.columns)}")
    print("\nDtypes:\n" + str(data.dtypes))
    print("\nNull counts:\n" + str(data.isna().sum()))
    if "InvoiceDate" in data.columns:
        print(f"\nDate range : {data['InvoiceDate'].min()} -> {data['InvoiceDate'].max()}")
    print("\nSample rows:\n" + data.head(3).to_string())

    data.to_parquet(OUT, engine="pyarrow", index=False)
    size_mb = OUT.stat().st_size / 1_000_000
    print(f"\nWrote {OUT} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
