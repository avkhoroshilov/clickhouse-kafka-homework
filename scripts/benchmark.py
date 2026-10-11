"""Сравнение исходного хранения, оптимизированной таблицы и агрегата."""

import argparse
import json
import statistics
import sys
import time

from common import ClickHouse, ROOT, write_text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", default="results/benchmark.json")
    args = parser.parse_args()
    if args.runs < 1:
        raise ValueError("--runs должен быть >= 1")
    client = ClickHouse()
    if not client.count():
        raise RuntimeError("Сначала загрузите CSV")
    client.query((ROOT / "sql/00_baseline.sql").read_text(encoding="utf-8"))
    # Производная таблица используется только этим скриптом.
    client.query("TRUNCATE TABLE homework.transactions_baseline")
    client.query("INSERT INTO homework.transactions_baseline SELECT * FROM homework.transactions")
    for table in ("transactions_baseline", "transactions", "state_max"):
        client.query(f"OPTIMIZE TABLE homework.{table} FINAL")

    raw = (ROOT / "sql/03_max_transaction_by_state_raw.sql").read_text(encoding="utf-8")
    queries = {
        "baseline": raw.replace("FROM homework.transactions\n", "FROM homework.transactions_baseline\n"),
        "optimized_raw": raw,
        "optimized_aggregate": (ROOT / "sql/02_max_transaction_by_state.sql").read_text(encoding="utf-8"),
    }
    results = {}
    reference = client.query(raw)
    for name, sql in queries.items():
        if client.query(sql) != reference:
            raise RuntimeError(f"Результат {name} отличается от исходного запроса")
        runs = []
        for _ in range(args.runs):
            start = time.perf_counter()
            _, run = client.query_with_stats(sql)
            elapsed = (time.perf_counter() - start) * 1000
            run["client_elapsed_ms"] = round(elapsed, 3)
            runs.append(run)
        results[name] = {"median_client_ms": round(statistics.median(r["client_elapsed_ms"] for r in runs), 3), "runs": runs}

    storage = client.query("""
        SELECT table, sum(rows) AS rows, sum(data_compressed_bytes) AS compressed_bytes,
               sum(data_uncompressed_bytes) AS uncompressed_bytes, sum(bytes_on_disk) AS bytes_on_disk
        FROM system.parts
        WHERE active AND database = 'homework'
          AND table IN ('transactions_baseline', 'transactions', 'state_max')
        GROUP BY table ORDER BY table FORMAT JSONEachRow
    """)
    report = {"clickhouse_version": client.query("SELECT version()").strip(),
              "runs_per_query": args.runs, "queries": results,
              "storage": [json.loads(line) for line in storage.splitlines()],
              "note": "Warm cache, one warmup, FINAL merges before measurements; milliseconds depend on hardware."}
    write_text(args.output, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(1)
