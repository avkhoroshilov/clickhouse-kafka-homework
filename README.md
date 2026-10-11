# CSV → Kafka → ClickHouse

Проект загружает транзакции из CSV в Kafka, сохраняет их в ClickHouse и определяет категорию самой большой отдельной транзакции по каждому штату, используются Kafka 3.9.1, ClickHouse 25.3.2.39 и Python 3.12.10. Kafka работает в режиме KRaft, без ZooKeeper.

## Требования

- Docker Engine / Docker Desktop с Docker Compose v2.24+.
- Рекомендуется 4 ГБ RAM и 5 ГБ свободного места.
- Свободные порты 8123 и 29092.

## Основные файлы

| Файл | Для чего |
| --- | --- |
| scripts/load_csv.py | Загрузка CSV в Kafka |
| scripts/run_pipeline.py | Полная загрузка, проверка и экспорт |
| sql/01_schema.sql | Оптимизированный DDL таблиц и materialized views |
| sql/02_max_transaction_by_state.sql | Основной запрос по штатам |
| sql/03_max_transaction_by_state_raw.sql | Контрольный запрос по исходным строкам |
| sql/00_baseline.sql | Хранение до оптимизации для сравнения |
| scripts/benchmark.py | Замер скорости и размера хранения |
| results/max_transaction_by_state.csv | Итоговый результат |

## Данные

Источник: [Kaggle](https://www.kaggle.com/t/1918f3f6435300327d38d6c596f97394), поместите файлы в data/train.csv и data/test.csv.

## Запуск и проверка

Выполните команды из корня проекта:

```bash
docker compose --profile tools build
docker compose up -d
docker compose run --rm app python scripts/run_pipeline.py data/train.csv data/test.csv --output results/max_transaction_by_state.csv
```

Загрузчик проверяет:
- совпадение количества строк CSV, подтверждений Kafka и записей ClickHouse;
- совпадение максимумов исходных CSV с обычным и оптимизированным SQL.
Успешный запуск печатает "status": "ok", 1048575 записей и 51 код штата/округа. Результат и отчёт сохраняются в results.

Для быстрого теста на пустой таблице вместо полной загрузки выполните:
```bash
docker compose run --rm app python scripts/run_pipeline.py data/demo.csv --output results/demo_state_max.csv
```
Ожидаемый результат: 16 записей, 5 штатов, "status": "ok"

## Оптимизация
Kafka Engine читает сообщения, а materialized view переносит их в MergeTree, второе представление обновляет агрегатную таблицу state_max.

Используются:
- LowCardinality(String) для повторяющихся значений
- сжатие ZSTD(3) и Delta для времени и номеров строк
- месячные партиции и сортировка по штату, времени и источнику
- AggregatingMergeTree с состояниями argMax для быстрого получения максимумов
- Основной запрос объединяет состояния через argMaxMerge, поэтому корректно работает до завершения фоновых слияний

Запуск замера после полной загрузки:
```bash
docker compose run --rm app python scripts/benchmark.py
```

Скрипт сравнивает baseline, оптимизированную полную таблицу и агрегат, результат сохраняется в results/benchmark.json

## Результаты проверки
Полный запуск проверен в Docker на macOS с ClickHouse 25.3.2.39. Все 1048575 записей доставлены, результаты обоих SQL совпали с исходными CSV.

После слияний и одного прогрева выполнено по три замера:

| Вариант | Медиана времени, мс | Прочитано строк | Сжатые данные, байт |
| --- | ---: | ---: | ---: |
| Baseline | 38.716 | 1 048 575 | 72 161 062 |
| Оптимизированная полная таблица | 32.228 | 1 048 575 | 42 889 033 |
| Запрос по агрегату | 2.746 | 51 | 1 614 |

Итоговый запрос ускорился примерно в 14 раз, сжатое хранение основной таблицы уменьшилось на 40.6%

## Повторный запуск
Перед повторной загрузкой или переходом с demo.csv на полный набор сбросьте данные Kafka и ClickHouse:

```bash
docker compose down -v
docker compose up -d
docker compose run --rm app python scripts/run_pipeline.py data/train.csv data/test.csv --output results/max_transaction_by_state.csv
```