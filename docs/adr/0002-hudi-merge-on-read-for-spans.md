# ADR 0002: Hudi Merge on Read for the spans table

- Status: accepted
- Date: 2026-11-09
- Owners: @member2, @member3

## Context

Spans arrive out of order and sometimes twice (collector retries, Kafka redelivery). The spans table is write heavy: every minute brings many small batches. Readers (Gold jobs, Trino) can tolerate slightly stale reads.

## Decision

Store Silver spans in Apache Hudi as a Merge on Read (MoR) table:

- Record key: `trace_id`, `span_id` (complex key generator).
- Precombine field: `end_ts`, so the latest version of a span wins.
- Partition path: `date` (from span start time).
- Operation: `upsert`.
- Compaction runs async from Airflow (`hudi_maintenance` DAG), not inline.

Gold tables are small and read heavy, so they use Copy on Write.

## Options considered

1. Plain Parquet with dedup at read time. Simple, but every reader pays for dedup and late data rewrites whole partitions.
2. Hudi Copy on Write. Fast reads, but each upsert rewrites Parquet files, which is expensive with frequent small batches.
3. Hudi Merge on Read. Cheap writes to log files, merged on read and compacted later.
4. Delta Lake or Iceberg. Both work. We picked Hudi for its record level index and built in upsert semantics on a key.

## Consequences

- Writes are cheap and idempotent on replay.
- Read optimized queries see only compacted data, so compaction lag matters. We track it in the data quality DAG.
- The Hudi bundle must match the Spark version (`hudi-spark3.5-bundle_2.12` for Spark 3.5).
