# ADR 0003: Trino as the SQL engine behind Grafana

- Status: accepted
- Date: 2026-11-09
- Owners: @member2, @member4

## Context

Grafana needs to read Gold and Silver tables with SQL, with response times of a few seconds. Spark is built for batch and streaming jobs, not for many small interactive queries.

## Decision

Run Trino with the Hudi connector and point Grafana at it through the `trino-datasource` plugin. Trino reads Hudi tables on MinIO with the native S3 file system.

The Hudi connector is read only and only sees tables registered in a metastore. For the scaffold, the catalog uses Trino's file based metastore in `s3://gold/_metastore`, so Trino starts and the Grafana datasource works, but no tables are listed. In the Core pipeline milestone we add a Hive Metastore service, switch the catalog to `thrift`, and enable Hudi hive sync in the Spark writers.

## Options considered

1. Spark Thrift Server. Same engine as the jobs, but heavy per query and slow to start sessions.
2. Export Gold to Postgres and query that. Fast, but duplicates data and adds a sync job.
3. Trino. Built for interactive SQL, has a Hudi connector, Grafana plugin exists.

## Consequences

- One more JVM (about 2 GB) in the `full` profile.
- Trino only reads Hudi, it does not write. All writes stay in Spark.
- Dashboards stay empty until the Hive Metastore and hive sync are in place.
