"""Небольшой HTTP-клиент ClickHouse; дополнительных зависимостей не нужно."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]


class ClickHouse:
    def __init__(self):
        self.url = os.getenv("CLICKHOUSE_URL", "http://localhost:8123").rstrip("/")
        self.user = os.getenv("CLICKHOUSE_USER", "homework")
        self.password = os.getenv("CLICKHOUSE_PASSWORD", "homework")
        self.opener = build_opener(ProxyHandler({}))

    def _request(self, sql):
        params = {"wait_end_of_query": 1}
        request = Request(
            self.url + "/?" + urlencode(params),
            data=sql.encode("utf-8"),
            headers={"X-ClickHouse-User": self.user, "X-ClickHouse-Key": self.password},
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=120) as response:
                result = response.read().decode("utf-8")
                summary = json.loads(response.headers.get("X-ClickHouse-Summary", "{}"))
                return result, summary
        except HTTPError as error:
            raise RuntimeError(error.read().decode("utf-8")[:1500]) from error

    def query(self, sql):
        return self._request(sql)[0]

    def query_with_stats(self, sql):
        result, summary = self._request(sql)
        if "read_rows" not in summary or "read_bytes" not in summary:
            raise RuntimeError("ClickHouse не вернул статистику X-ClickHouse-Summary")
        metrics = {"read_rows": int(summary["read_rows"]), "read_bytes": int(summary["read_bytes"])}
        if "elapsed_ns" in summary:
            metrics["engine_elapsed_ms"] = round(int(summary["elapsed_ns"]) / 1_000_000, 3)
        if "memory_usage" in summary:
            metrics["memory_usage"] = int(summary["memory_usage"])
        return result, metrics

    def count(self):
        return int(self.query("SELECT count() FROM homework.transactions"))


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
