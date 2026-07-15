"""
config.py — koneksi ke database Neon PostgreSQL.
Membaca connection string dari .env agar kredensial tidak masuk kode/GitHub.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL tidak ditemukan. Cek file .env")

engine = create_engine(DATABASE_URL)

if __name__ == "__main__":
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        print("Koneksi berhasil!")
        print(result.fetchone()[0])