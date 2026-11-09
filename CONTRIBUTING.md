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

We use three kinds of branches.

| Branch | Purpose | Receives merges from |
|---|---|---|
| `main` | Stable. Always runs. | `develop`, at the end of each milestone |
| `develop` | Integration branch. Default target for all PRs. | Feature branches, by PR |
| `feat/...`, `fix/...`, `docs/...`, `chore/...` | One change each. | Nobody, they are merged and deleted |

### Feature branches

Create them from `develop` and name them `<type>/<area>-<topic>`, where type is `feat`, `fix`, `docs` or `chore`:

- `feat/spark-silver-spans`
- `fix/otel-kafka-encoding`
- `docs/lakehouse-table-design`
- `chore/compose-bump-grafana`

```
git switch develop
git pull
git switch -c feat/spark-silver-spans
```

Keep branches short lived. Rebase on `develop` before opening a PR, and open the PR against `develop`. Someone from another area reviews it. Delete the branch after the merge.

### Releases

At the end of each milestone (see the roadmap in the README), we merge `develop` into `main` with a PR and tag the merge commit:

```
git switch main
git pull
git tag -a v0.1.0 -m "v0.1.0: foundations"
git push origin v0.1.0
```

Tags follow [semantic versioning](https://semver.org/): `v0.x.0` per milestone until `v1.0.0`.

Nobody pushes directly to `main` or `develop`.

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

- PRs target `develop`. Only release PRs target `main`.
- Every PR is reviewed by someone from another area. A Spark change gets a review from services, lakehouse or orchestration, not from Spark.
- `main` must always run. If `make up` breaks on `main`, fixing it comes before anything else. `develop` should run too: if it breaks, fix it before merging new features.
- CI must be green before merge.
- Fill in the PR template, including how you tested.

## Definition of done

A change is done when all of these are true:

1. It is merged to `develop`. It reaches `main` with the next milestone release.
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
