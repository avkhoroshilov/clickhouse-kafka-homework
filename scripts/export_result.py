"""Повторный экспорт результата без повторной отправки CSV в Kafka."""

import argparse
import sys

from common import ClickHouse, ROOT, write_text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/max_transaction_by_state.csv")
    args = parser.parse_args()
    client = ClickHouse()
    if not client.count():
        raise RuntimeError("В ClickHouse пока нет транзакций")
    sql = (ROOT / "sql/02_max_transaction_by_state.sql").read_text(encoding="utf-8")
    write_text(args.output, client.query(sql))
    print(f"Результат сохранён: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(1)
