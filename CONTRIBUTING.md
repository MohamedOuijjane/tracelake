# Contributing

Thanks for helping out. This page covers how we work on tracelake.

## Areas and owners

| Area | Paths | Owner |
|---|---|---|
| Services and ingestion | `services/`, `otel/`, `loadgen/`, `kafka/` | @member1 |
| Lakehouse and contracts | `lakehouse/`, `contracts/` | @member2 |
| Spark jobs | `spark/` | @member3 |
| Orchestration, dashboards, CI | `airflow/`, `grafana/`, `.github/` | @member4 |

The source of truth is [.github/CODEOWNERS](.github/CODEOWNERS).

## Branches

Use `feat/<area>-<topic>`, for example:

- `feat/spark-silver-spans`
- `feat/compose-trino-healthcheck`
- `fix/otel-kafka-encoding`

Keep branches short lived. Rebase on `main` before opening a PR.

## Commits

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(spark): add p99 to red metrics
fix(compose): raise kafka heap to 1g
docs(adr): record trino as grafana engine
chore: bump grafana to 11.5.2
```

Keep the subject under 72 characters and in the imperative mood.

## Pull requests

- Every PR is reviewed by someone from another area. A Spark change gets a review from services, lakehouse or orchestration, not from Spark.
- `main` must always run. If `make up` breaks on `main`, fixing it comes before anything else.
- CI must be green before merge.
- Fill in the PR template, including how you tested.

## Definition of done

A change is done when all of these are true:

1. It is merged to `main`.
2. It runs under `make up` (or the profile it belongs to: `make up-full`, `make demo`).
3. It is documented: README, the component README, or an ADR for design decisions.

## Local checks

```
make lint
make test
docker compose --profile full config -q
```

## Architecture decisions

Significant design choices get an ADR in [docs/adr](docs/adr). Copy [template.md](docs/adr/template.md), take the next number and open it with the PR that implements it.
