FROM golang:1.23.6-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/restaurants .

FROM alpine:3.21.3
RUN adduser -D -u 10001 app
COPY --from=build /out/restaurants /usr/local/bin/restaurants
USER app
EXPOSE 8080
# The OTel SDK reads OTEL_SERVICE_NAME and OTEL_EXPORTER_OTLP_ENDPOINT from the environment.
ENTRYPOINT ["/usr/local/bin/restaurants"]
