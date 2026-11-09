#!/bin/sh
# Create lakehouse buckets on MinIO. Safe to run many times.
set -eu

ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"

mc alias set local "$ENDPOINT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

for bucket in bronze silver gold checkpoints; do
  mc mb --ignore-existing "local/$bucket"
done

mc ls local
