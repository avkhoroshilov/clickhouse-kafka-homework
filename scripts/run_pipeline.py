"""Загрузка CSV, ожидание ClickHouse, сверка результата и экспорт CSV."""

import argparse
import csv
import io
import json
import sys
import time
from decimal import Decimal
from pathlib import Path

from common import ClickHouse, ROOT, write_text
from load_csv import load_files


def parse_result(text):
    return [
        (row["us_state"], row["cat_id"], Decimal(row["max_amount"]), row["source_file"], int(row["source_row"]))
        for row in csv.DictReader(io.StringIO(text))
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="+")
    parser.add_argument("--output", default="results/max_transaction_by_state.csv")
    parser.add_argument("--timeout", type=int, default=300, help="Ожидание загрузки в ClickHouse, секунд")
    args = parser.parse_args()
    client = ClickHouse()
    if client.count():
        raise RuntimeError("Таблица уже содержит данные. Для нового полного прогона выполните сброс из README.")

    started = time.perf_counter()
    loaded = load_files(args.csv)
    deadline = time.monotonic() + args.timeout
    while True:
        actual_count = client.count()
        if actual_count == loaded["rows"]:
            break
        if actual_count > loaded["rows"]:
            raise RuntimeError(f"В ClickHouse лишние записи: {actual_count} > {loaded['rows']}")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Не все данные дошли до ClickHouse: {actual_count}/{loaded['rows']}")
        print(f"ClickHouse: {actual_count:,}/{loaded['rows']:,}", file=sys.stderr, flush=True)
        time.sleep(1)

    optimized_sql = (ROOT / "sql/02_max_transaction_by_state.sql").read_text(encoding="utf-8")
    raw_sql = (ROOT / "sql/03_max_transaction_by_state_raw.sql").read_text(encoding="utf-8")
    expected = [
        (state, row["cat_id"], Decimal(row["amount"]), row["source_file"], row["source_row"])
        for state, row in sorted(loaded["winners"].items())
    ]
    # Каскадное представление может завершить обновление чуть позже основной таблицы.
    while True:
        result_csv = client.query(optimized_sql)
        if parse_result(result_csv) == expected:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError("Агрегированный результат не совпал с максимумами исходных CSV")
        time.sleep(1)
    if parse_result(client.query(raw_sql)) != expected:
        raise RuntimeError("Запрос по исходным строкам не совпал с максимумами CSV")

    write_text(args.output, result_csv)
    report = {
        "status": "ok", "input_files": loaded["files"],
        "csv_rows": loaded["rows"], "kafka_delivered": loaded["delivered"],
        "clickhouse_rows": actual_count, "states": len(expected),
        "checks": ["CSV row count = Kafka deliveries = ClickHouse row count", "CSV maxima = raw SQL = optimized SQL"],
        "result_csv": str(args.output), "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    report_path = Path(args.output).with_suffix(".report.json")
    write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(1)
