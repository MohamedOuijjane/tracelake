FROM alpine:3.20 AS jdbc

RUN apk add --no-cache curl \
    && curl -fsSL \
       https://repo.maven.apache.org/maven2/org/postgresql/postgresql/42.7.5/postgresql-42.7.5.jar \
       -o /postgres.jar

FROM apache/hive:4.0.1

COPY --from=jdbc /postgres.jar /opt/hive/lib/postgres.jar
