package io.tracelake.orders;

import java.math.BigDecimal;
import java.net.http.HttpClient;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Places food orders. One POST /orders calls, in this order: restaurants (availability and
 * preparation time), payments (charge), delivery (courier and ETA). The order row is stored in
 * Postgres and updated after each step.
 *
 * The OpenTelemetry Java agent instruments the RestClient calls: each one is a CLIENT span that
 * sends the W3C traceparent header, so the downstream SERVER spans join the same trace.
 *
 * The HTTP client is pinned to HTTP/1.1. By default the JDK client sends an "Upgrade: h2c"
 * header on cleartext requests. uvicorn (payments, delivery) does not support it and, on a reused
 * keep-alive connection, its instrumentation then records a SERVER span only for the first
 * request, which leaves most CLIENT spans without a child SERVER span.
 */
@RestController
@RequestMapping("/orders")
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);

    public record Item(String dishId, int quantity) {}

    public record CreateOrder(String restaurantId, List<Item> items, String address) {}

    record CheckResult(String restaurantId, boolean available, BigDecimal total, int preparationMinutes) {}

    record PaymentResult(String paymentId, String status) {}

    record DeliveryResult(String deliveryId, String courierId, int etaMinutes, String status) {}

    private final OrderRepository repository;
    private final ObjectMapper json;
    private final RestClient restaurants;
    private final RestClient payments;
    private final RestClient delivery;

    public OrderController(OrderRepository repository,
                           ObjectMapper json,
                           RestClient.Builder builder,
                           @Value("${restaurants.url}") String restaurantsUrl,
                           @Value("${payments.url}") String paymentsUrl,
                           @Value("${delivery.url}") String deliveryUrl) {
        this.repository = repository;
        this.json = json;
        JdkClientHttpRequestFactory http11 = http11RequestFactory();
        this.restaurants = builder.clone().requestFactory(http11).baseUrl(restaurantsUrl).build();
        this.payments = builder.clone().requestFactory(http11).baseUrl(paymentsUrl).build();
        this.delivery = builder.clone().requestFactory(http11).baseUrl(deliveryUrl).build();
    }

    /** One shared HTTP/1.1 client, with the same timeouts as spring.http.client in application.yml. */
    private static JdkClientHttpRequestFactory http11RequestFactory() {
        HttpClient client = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(2))
                .build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(client);
        factory.setReadTimeout(Duration.ofSeconds(5));
        return factory;
    }

    @PostMapping
    public ResponseEntity<?> create(@RequestBody CreateOrder request) throws JsonProcessingException {
        if (request.restaurantId() == null || request.items() == null || request.items().isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("error", "restaurant_id and items are required"));
        }
        validate();
        Order order = new Order(request.restaurantId(), json.writeValueAsString(request.items()),
                request.address(), "PENDING");

        // 1. Restaurant: are the dishes available, how long will they take?
        CheckResult check;
        try {
            check = restaurants.post()
                    .uri("/restaurants/{id}/check", request.restaurantId())
                    .body(Map.of("items", request.items()))
                    .retrieve()
                    .body(CheckResult.class);
        } catch (HttpClientErrorException.NotFound e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("error", "unknown restaurant"));
        } catch (HttpClientErrorException.Conflict e) {
            // Business rejection: a dish is unknown or unavailable.
            order.status("REJECTED");
            return ResponseEntity.status(HttpStatus.CONFLICT).body(repository.save(order));
        } catch (RestClientException e) {
            order.status("CHECK_FAILED");
            return dependencyFailed("restaurants", repository.save(order), e);
        }
        order.priced(check.total(), check.preparationMinutes());
        order = repository.save(order);

        // 2. Payment: charge the total.
        try {
            PaymentResult payment = payments.post()
                    .uri("/payments")
                    .body(Map.of("order_id", order.getId(), "amount", check.total()))
                    .retrieve()
                    .body(PaymentResult.class);
            order.paid(payment.paymentId());
        } catch (HttpClientErrorException e) {
            // Business rejection by payments (4xx): the charge was refused.
            order.status("PAYMENT_FAILED");
            return ResponseEntity.status(HttpStatus.PAYMENT_REQUIRED).body(repository.save(order));
        } catch (RestClientException e) {
            order.status("PAYMENT_ERROR");
            return dependencyFailed("payments", repository.save(order), e);
        }

        // 3. Delivery: assign a courier.
        try {
            DeliveryResult courier = delivery.post()
                    .uri("/deliveries")
                    .body(Map.of(
                            "order_id", order.getId(),
                            "restaurant_id", request.restaurantId(),
                            "preparation_minutes", check.preparationMinutes(),
                            "address", request.address() == null ? "unknown" : request.address()))
                    .retrieve()
                    .body(DeliveryResult.class);
            order.dispatched(courier.courierId(), courier.etaMinutes());
            order.status("CONFIRMED");
        } catch (RestClientException e) {
            // Paid but no courier: the order row keeps the payment id for a later retry.
            order.status("DELIVERY_FAILED");
            return dependencyFailed("delivery", repository.save(order), e);
        }
        return ResponseEntity.status(HttpStatus.CREATED).body(repository.save(order));
    }

    /**
     * A dependency answered 5xx, an unexpected 4xx, or could not be reached: answer 502 and name it.
     * The 5xx status makes the orders SERVER span ERROR, so detection sees that orders is affected.
     */
    private ResponseEntity<Map<String, Object>> dependencyFailed(String dependency, Order order,
                                                                 RestClientException e) {
        String detail = e instanceof HttpStatusCodeException http
                ? "HTTP " + http.getStatusCode().value()
                : e instanceof ResourceAccessException
                        ? "connection error: " + rootCause(e).getClass().getSimpleName()
                        : e.getClass().getSimpleName();
        log.warn("order {}: {} failed ({})", order.getId(), dependency, detail);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("error", "dependency failed");
        body.put("dependency", dependency);
        body.put("detail", detail);
        body.put("order_id", order.getId());
        body.put("status", order.getStatus());
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(body);
    }

    private static Throwable rootCause(Throwable e) {
        while (e.getCause() != null && e.getCause() != e) {
            e = e.getCause();
        }
        return e;
    }

    @GetMapping("/{id}")
    public ResponseEntity<Order> get(@PathVariable Long id) {
        return repository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /** Simulates request validation and fraud rules so the orders span has its own latency. */
    private static void validate() {
        try {
            Thread.sleep(ThreadLocalRandom.current().nextLong(5, 25));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
