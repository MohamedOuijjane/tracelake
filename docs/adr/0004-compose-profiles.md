# ADR 0004: One compose file with profiles

- Status: accepted
- Date: 2026-11-09
- Owners: @member4

## Context

The full stack needs about 16 GB of RAM. Most of the time a developer works on one part: Spark jobs need Kafka and MinIO, not Grafana. We also want one command to start a full demo.

## Decision

Keep a single `docker-compose.yml` and use Compose profiles:

- `core`: Kafka, MinIO, Spark. Fits in 8 GB.
- `full`: core + collector, services, Postgres, Airflow, Trino, Grafana.
- `demo`: full + k6 load generator.

Each service lists every profile it belongs to. Every service has a healthcheck, a memory limit, and uses `depends_on` with `condition: service_healthy`. The Makefile wraps the profile flags (`make up`, `make up-full`, `make demo`).

## Options considered

1. Several compose files merged with `-f`. Flexible, but easy to drift and hard to read.
2. One file, no profiles. Simple, but too heavy for laptops.
3. One file with profiles. Single source of truth, light by default.

## Consequences

- Adding a service means choosing its profiles explicitly.
- CI validates each profile with `docker compose --profile <p> config -q`.
