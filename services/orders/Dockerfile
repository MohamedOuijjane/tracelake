FROM maven:3.9.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -q -B dependency:go-offline
COPY src ./src
RUN mvn -q -B package -DskipTests

FROM eclipse-temurin:21-jre-jammy
ARG OTEL_AGENT_VERSION=2.12.0
WORKDIR /app
ADD https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v${OTEL_AGENT_VERSION}/opentelemetry-javaagent.jar /otel/opentelemetry-javaagent.jar
RUN chmod 644 /otel/opentelemetry-javaagent.jar && useradd --system --uid 10001 app
COPY --from=build /src/target/orders-0.1.0.jar /app/app.jar
USER app
# The agent reads OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT and friends from the environment.
ENV JAVA_TOOL_OPTIONS="-javaagent:/otel/opentelemetry-javaagent.jar -XX:MaxRAMPercentage=70"
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
