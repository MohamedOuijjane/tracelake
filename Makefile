SHELL := /bin/bash
COMPOSE := docker compose
CORE := $(COMPOSE) --profile core
FULL := $(COMPOSE) --profile full
DEMO := $(COMPOSE) --profile demo
ALL  := $(COMPOSE) --profile core --profile full --profile demo

.DEFAULT_GOAL := help
.PHONY: help env up up-full demo down clean topics logs ps test test-spark test-dags lint seed bronze order dlq-peek bad-message chaos heal chaos-status

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  %-12s %s\n", $$1, $$2}'

env:
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example")

# Init jobs (kafka-init, minio-init, airflow-init) exit when done, and "up --wait" treats any
# exit as a failure. So we start everything, then wait on the long-running services only.
CORE_SERVICES := kafka minio spark-master spark-worker
FULL_SERVICES := $(CORE_SERVICES) otel-collector kafka-ui toxiproxy gateway airflow-webserver airflow-scheduler trino grafana

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

dlq-peek: ## Print the last 10 messages of otel.traces.dlq
	$(CORE) exec -T kafka bash /opt/tracelake/kafka/dlq-peek.sh

bad-message: ## Send one malformed (non JSON) message to otel.traces to test the DLQ path
	echo 'not json: {"resourceSpans": [' | $(CORE) exec -T -e KAFKA_HEAP_OPTS=-Xmx128m kafka \
	  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 --topic otel.traces
	@echo "sent one malformed message to otel.traces"

chaos: ## Inject fault F1 (2 s latency on orders -> payments) and record it in incidents.csv
	bash loadgen/chaos/chaos.sh start F1

heal: ## Remove all toxics and close the open incident in incidents.csv
	bash loadgen/chaos/chaos.sh heal

chaos-status: ## Show active toxics and the open incident
	bash loadgen/chaos/chaos.sh status

order: ## Place one food order through the gateway (needs the full profile)
	curl -fsS -X POST localhost:8000/api/orders -H 'Content-Type: application/json' \
	  -d '{"restaurant_id":"1","items":[{"dish_id":"pz-margherita","quantity":2}],"address":"12 Rue de la Paix"}'
	@echo

bronze: ## Start the Bronze streaming job on the Spark cluster (log: /tmp/bronze_ingest.log)
	$(CORE) exec -d spark-master bash -c "bash /opt/tracelake/spark/submit.sh bronze_ingest > /tmp/bronze_ingest.log 2>&1"
	@echo "follow with: docker compose exec spark-master tail -f /tmp/bronze_ingest.log"
