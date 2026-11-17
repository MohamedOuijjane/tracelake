package io.tracelake.gateway;

import java.time.Duration;
import java.util.concurrent.ThreadLocalRandom;

import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;

import reactor.core.publisher.Mono;

/**
 * Adds 2 to 15 ms before each routed request to stand in for auth and rate limiting at the edge.
 * The delay is non blocking, so the gateway threads stay free.
 */
@Component
public class ProcessingDelayFilter implements GlobalFilter, Ordered {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        long ms = ThreadLocalRandom.current().nextLong(2, 16);
        return Mono.delay(Duration.ofMillis(ms)).then(chain.filter(exchange));
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }
}
