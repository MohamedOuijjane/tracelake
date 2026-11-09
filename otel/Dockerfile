# The contrib image has no shell or HTTP client, so a Docker healthcheck cannot call
# the health_check extension. We copy a static busybox wget in for that purpose only.
FROM busybox:1.37.0-musl AS tools

FROM otel/opentelemetry-collector-contrib:0.120.0
COPY --from=tools /bin/busybox /bin/wget
COPY collector-config.yaml /etc/otelcol-contrib/config.yaml
