# Hive Metastore — TraceLake

## Overview

TraceLake uses Apache Hive Metastore backed by PostgreSQL to manage metadata for Hudi tables stored in MinIO.

- **PostgreSQL:** persists Metastore metadata.
- **Hive Metastore:** exposes metadata through Thrift on port `9083`.
- **Trino:** accesses the Hive Metastore using the Hudi catalog.
- **MinIO:** stores the actual lakehouse data files.

## Configuration

The following environment variables must be set in `.env`:

```dotenv
HIVE_DB_NAME=metastore_db
HIVE_DB_USER=hive
HIVE_DB_PASSWORD=<local-password>
```

The Hive Metastore Docker image is built from `lakehouse/hive-metastore/Dockerfile`, which adds the PostgreSQL JDBC driver to Apache Hive 4.0.1.

## Start the services

From the project root:

```powershell
docker compose --profile full up -d --build hive-metastore
docker compose --profile full up -d trino
```

## Verify the services

Check Hive Metastore health:

```powershell
docker compose --profile full ps hive-metastore
```

Expected status: `healthy`.

Query the Hudi catalog through Trino:

```powershell
docker compose --profile full exec trino trino --execute "SHOW SCHEMAS FROM hudi"
```

A fresh Metastore should return at least `default` and `information_schema`.

## Next steps

The Spark Silver Hudi jobs must register and synchronize their table metadata with this Hive Metastore. Once the `silver.spans` table is populated and registered, it can be queried through Trino.

**Note:** Successful `SHOW SCHEMAS` execution validates Metastore connectivity but does not yet validate reads from populated Hudi tables.
