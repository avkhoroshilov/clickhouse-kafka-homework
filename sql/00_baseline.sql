-- Учебный DDL до оптимизации. Не выполняется при обычном старте.
-- benchmark.py создаёт и наполняет эту таблицу для сравнения.
CREATE TABLE IF NOT EXISTS homework.transactions_baseline
(
    transaction_time DateTime('UTC'),
    merch String,
    cat_id String,
    amount Decimal(18, 2),
    name_1 String,
    name_2 String,
    gender String,
    street String,
    one_city String,
    us_state String,
    post_code String,
    lat Float64,
    lon Float64,
    population_city UInt64,
    jobs String,
    merchant_lat Float64,
    merchant_lon Float64,
    target Nullable(UInt8),
    source_file String,
    source_row UInt64
)
ENGINE = MergeTree
ORDER BY tuple();
