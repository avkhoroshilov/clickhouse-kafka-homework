SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
.NOTPARALLEL: all
DBT ?= dbt
SQLFLUFF ?= sqlfluff
DBT_FLAGS ?= --profiles-dir .

.PHONY: deps seed run test unit lint fix docs serve all

deps:
	$(DBT) deps $(DBT_FLAGS)

seed:
	$(DBT) seed $(DBT_FLAGS)

run:
	$(DBT) run $(DBT_FLAGS)

test:
	mkdir -p evidence
	$(DBT) test $(DBT_FLAGS) --no-use-colors 2>&1 | tee evidence/dbt-test.log

unit:
	$(DBT) test $(DBT_FLAGS) --select test_type:unit

lint:
	mkdir -p evidence
	$(SQLFLUFF) lint models tests 2>&1 | tee evidence/sqlfluff.log

fix:
	$(SQLFLUFF) fix models tests

docs:
	$(DBT) docs generate $(DBT_FLAGS) --static

serve:
	$(DBT) docs serve $(DBT_FLAGS) --host 127.0.0.1 --port 8080

all: deps seed run test lint docs
