SHELL := /bin/bash
COMPOSE := docker compose
CORE := $(COMPOSE) --profile core
FULL := $(COMPOSE) --profile full
DEMO := $(COMPOSE) --profile demo
ALL  := $(COMPOSE) --profile core --profile full --profile demo

.DEFAULT_GOAL := help
.PHONY: help env up up-full demo down clean topics logs ps test test-spark test-dags lint seed bronze

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  %-10s %s\n", $$1, $$2}'

env:
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example")

# Init jobs (kafka-init, minio-init, airflow-init) exit when done, and "up --wait" treats any
# exit as a failure. So we start everything, then wait on the long-running services only.
CORE_SERVICES := kafka minio spark-master spark-worker
FULL_SERVICES := $(CORE_SERVICES) otel-collector gateway airflow-webserver airflow-scheduler trino grafana

up: env ## Start the core profile (Kafka, MinIO, Spark)
	$(CORE) up -d
	$(CORE) up -d --wait --no-recreate $(CORE_SERVICES)

up-full: env ## Start the full profile (core + services, Airflow, Trino, Grafana)
	$(FULL) up -d --build
	$(FULL) up -d --wait --no-recreate $(FULL_SERVICES)

demo: env ## Start the full profile plus the k6 load generator
	$(DEMO) up -d --build

down: ## Stop all containers, keep volumes
	$(ALL) down

clean: ## Stop all containers and remove volumes
	$(ALL) down -v --remove-orphans

topics: ## Create Kafka topics (idempotent)
	$(CORE) exec -T kafka bash /opt/tracelake/kafka/create-topics.sh

logs: ## Follow logs (make logs s=kafka for one service)
	$(ALL) logs -f --tail=100 $(s)

ps: ## Show container status
	$(ALL) ps

test: test-spark test-dags ## Run Spark unit tests and Airflow DAG import tests

test-spark:
	cd spark && python -m pytest -q

test-dags:
	python -m pytest -q airflow/tests

lint: ## Run ruff on all Python code
	ruff check .
	ruff format --check .

seed: ## Push sample OTLP spans to otel.traces
	$(CORE) exec -T kafka bash /opt/tracelake/kafka/seed-sample-spans.sh

bronze: ## Start the Bronze streaming job on the Spark cluster (log: /tmp/bronze_ingest.log)
	$(CORE) exec -d spark-master bash -c "bash /opt/tracelake/spark/submit.sh bronze_ingest > /tmp/bronze_ingest.log 2>&1"
	@echo "follow with: docker compose exec spark-master tail -f /tmp/bronze_ingest.log"
