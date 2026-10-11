-- Финальный оптимизированный DDL: пункты 2 и 4 задания.
-- Представление для агрегатов создаётся ДО подключения потока Kafka.
CREATE DATABASE IF NOT EXISTS homework;

CREATE TABLE IF NOT EXISTS homework.transactions
(
    transaction_time DateTime('UTC') CODEC(Delta, ZSTD(3)),
    merch String CODEC(ZSTD(3)),
    cat_id LowCardinality(String),
    amount Decimal(18, 2) CODEC(ZSTD(3)),
    name_1 String CODEC(ZSTD(3)),
    name_2 String CODEC(ZSTD(3)),
    gender LowCardinality(String),
    street String CODEC(ZSTD(3)),
    one_city LowCardinality(String),
    us_state LowCardinality(String),
    post_code String CODEC(ZSTD(3)),
    lat Float64 CODEC(ZSTD(3)),
    lon Float64 CODEC(ZSTD(3)),
    population_city UInt64 CODEC(ZSTD(3)),
    jobs LowCardinality(String),
    merchant_lat Float64 CODEC(ZSTD(3)),
    merchant_lon Float64 CODEC(ZSTD(3)),
    target Nullable(UInt8),
    source_file LowCardinality(String),
    source_row UInt64 CODEC(Delta, ZSTD(3))
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(transaction_time)
ORDER BY (us_state, transaction_time, source_file, source_row);

CREATE TABLE IF NOT EXISTS homework.state_max
(
    us_state String,
    winner AggregateFunction(
        argMax,
        Tuple(String, Decimal(18, 2), String, UInt64),
        Tuple(Decimal(18, 2), String, String, UInt64)
    )
)
ENGINE = AggregatingMergeTree
ORDER BY us_state;

CREATE MATERIALIZED VIEW IF NOT EXISTS homework.transactions_to_state_max
TO homework.state_max
AS
SELECT
    toString(us_state) AS us_state,
    argMaxState(
        tuple(toString(cat_id), amount, toString(source_file), source_row),
        tuple(amount, toString(cat_id), toString(source_file), source_row)
    ) AS winner
FROM homework.transactions
GROUP BY us_state;

CREATE TABLE IF NOT EXISTS homework.transactions_kafka
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
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:9092',
    kafka_topic_list = 'transactions',
    kafka_group_name = 'clickhouse-homework-v1',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1,
    kafka_max_block_size = 65536,
    kafka_flush_interval_ms = 1000,
    kafka_skip_broken_messages = 0;

CREATE MATERIALIZED VIEW IF NOT EXISTS homework.kafka_to_transactions
TO homework.transactions
AS
SELECT transaction_time, merch, cat_id, amount, name_1, name_2, gender, street, one_city, us_state, post_code, lat, lon, population_city, jobs, merchant_lat, merchant_lon, target, source_file, source_row
FROM homework.transactions_kafka;
