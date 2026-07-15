CREATE TABLE dim_date (
    date_key        INTEGER PRIMARY KEY,   -- YYYYMMDD, mis. 20101201
    full_date       DATE NOT NULL,
    year            SMALLINT NOT NULL,
    quarter         SMALLINT NOT NULL,
    month           SMALLINT NOT NULL,
    month_name      VARCHAR(10) NOT NULL,
    day_of_month    SMALLINT NOT NULL,
    day_of_week     SMALLINT NOT NULL,     -- 1=Senin .. 7=Minggu
    day_name        VARCHAR(10) NOT NULL,
    is_weekend      BOOLEAN NOT NULL,
    week_of_year    SMALLINT NOT NULL
);

CREATE TABLE dim_product (
    product_key     SERIAL PRIMARY KEY,    -- surrogate key: auto-increment 1,2,3...
    stock_code      VARCHAR(20) NOT NULL,  -- natural key dari sumber (85123A, POST, ...)
    description     VARCHAR(255),          -- boleh NULL (ingat 1.454 baris tanpa deskripsi)
    category        VARCHAR(50),           -- diisi nanti lewat rule-based categorization
    is_product      BOOLEAN DEFAULT TRUE,  -- FALSE untuk POST, M, BANK CHARGES, dll
    UNIQUE (stock_code)                    -- natural key wajib unik
);

CREATE TABLE dim_customer (
    customer_key  INTEGER PRIMARY KEY,
    customer_id   VARCHAR(20) NOT NULL,
    country       VARCHAR(50) NOT NULL,
    UNIQUE (customer_id, country)
);

INSERT INTO dim_customer (customer_key, customer_id, country)
VALUES (-1, 'UNKNOWN', 'Unknown');

CREATE TABLE fact_sales (
    sales_key         BIGSERIAL PRIMARY KEY,
    date_key          INTEGER NOT NULL REFERENCES dim_date(date_key),
    product_key       INTEGER NOT NULL REFERENCES dim_product(product_key),
    customer_key      INTEGER NOT NULL REFERENCES dim_customer(customer_key),
    invoice_no        VARCHAR(20) NOT NULL,
    quantity          INTEGER NOT NULL,
    unit_price        NUMERIC(10,2) NOT NULL,
    revenue           NUMERIC(12,2) NOT NULL,
    transaction_type  VARCHAR(15) NOT NULL
);

