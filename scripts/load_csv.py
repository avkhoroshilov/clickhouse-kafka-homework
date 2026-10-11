"""Потоковая загрузка train/test CSV в Kafka: одна запись — одно JSON-сообщение."""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from confluent_kafka import Producer

REQUIRED = {
    "transaction_time", "merch", "cat_id", "amount", "name_1", "name_2",
    "gender", "street", "one_city", "us_state", "post_code", "lat", "lon",
    "population_city", "jobs", "merchant_lat", "merchant_lon",
}
FLOAT_FIELDS = ("lat", "lon", "merchant_lat", "merchant_lon")


def csv_records(paths):
    for path in map(Path, paths):
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            missing = REQUIRED - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path.name}: отсутствуют колонки {', '.join(sorted(missing))}")
            for number, row in enumerate(reader, 1):
                try:
                    record = {key: row[key] for key in REQUIRED}
                    amount = Decimal(row["amount"])
                    if not amount.is_finite() or abs(amount) >= Decimal("10000000000000000"):
                        raise ValueError("amount не помещается в Decimal(18,2)")
                    rounded = amount.quantize(Decimal("0.01"))
                    if rounded != amount:
                        raise ValueError("amount содержит больше двух знаков после запятой")
                    record["amount"] = format(rounded, ".2f")
                    instant = datetime.fromisoformat(row["transaction_time"])
                    if instant.tzinfo:
                        instant = instant.astimezone(timezone.utc)
                    record["transaction_time"] = instant.strftime("%Y-%m-%d %H:%M:%S")
                    for key in FLOAT_FIELDS:
                        record[key] = float(row[key])
                    record["population_city"] = int(row["population_city"])
                    record["target"] = int(row["target"]) if row.get("target") else None
                    record["source_file"] = path.name
                    record["source_row"] = number
                    if not record["us_state"] or not record["cat_id"]:
                        raise ValueError("us_state и cat_id должны быть заполнены")
                except (ValueError, TypeError, ArithmeticError) as error:
                    raise ValueError(f"{path.name}: запись {number}: {error}") from error
                yield record


def winner_key(record):
    return (
        Decimal(record["amount"]), record["cat_id"],
        record["source_file"], record["source_row"],
    )


def load_files(paths, bootstrap_servers=None):
    producer = Producer({
        "bootstrap.servers": bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092"),
        "enable.idempotence": True,
        "acks": "all",
        "compression.type": "lz4",
        "linger.ms": 50,
        "queue.buffering.max.kbytes": 65536,
        "delivery.timeout.ms": 120000,
    })
    delivered = 0
    failure = None

    def on_delivery(error, message):
        nonlocal delivered, failure
        if error is not None:
            failure = error
        else:
            delivered += 1

    rows = 0
    file_counts = {}
    winners = {}
    for record in csv_records(paths):
        if failure:
            raise RuntimeError(f"Ошибка доставки Kafka после {delivered} записей: {failure}")
        data = json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        while True:
            try:
                producer.produce(
                    "transactions", key=record["us_state"].encode("utf-8"),
                    value=data, on_delivery=on_delivery,
                )
                break
            except BufferError:
                producer.poll(0.1)
                if failure:
                    raise RuntimeError(f"Ошибка доставки Kafka: {failure}")
        producer.poll(0)
        rows += 1
        file_counts[record["source_file"]] = record["source_row"]
        state = record["us_state"]
        current = winners.get(state)
        if current is None or winner_key(record) > winner_key(current):
            winners[state] = record
        if rows % 100000 == 0:
            print(f"Отправлено {rows:,}; подтверждено Kafka: {delivered:,}", file=sys.stderr, flush=True)

    pending = producer.flush(120)
    if pending or failure or delivered != rows:
        raise RuntimeError(f"Доставка не завершена: rows={rows}, delivered={delivered}, pending={pending}, error={failure}")
    if not rows:
        raise ValueError("В CSV нет записей")
    return {"rows": rows, "delivered": delivered, "files": file_counts, "winners": winners}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="+", help="Пути к train.csv и/или test.csv")
    args = parser.parse_args()
    result = load_files(args.csv)
    print(json.dumps({key: value for key, value in result.items() if key != "winners"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(1)
