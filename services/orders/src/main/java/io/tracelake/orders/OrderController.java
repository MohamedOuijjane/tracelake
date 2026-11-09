package io.tracelake.orders;

import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@RestController
@RequestMapping("/orders")
public class OrderController {

    public record CreateOrder(String sku, int quantity) {}

    private final OrderRepository repository;
    private final RestClient inventory;

    public OrderController(OrderRepository repository,
                           RestClient.Builder builder,
                           @Value("${inventory.url}") String inventoryUrl) {
        this.repository = repository;
        this.inventory = builder.baseUrl(inventoryUrl).build();
    }

    /** Places an order: reserves stock in inventory, then stores the order. */
    @PostMapping
    public ResponseEntity<Order> create(@RequestBody CreateOrder request) {
        String status;
        try {
            inventory.post()
                    .uri("/inventory/reserve")
                    .body(Map.of("sku", request.sku(), "quantity", request.quantity()))
                    .retrieve()
                    .toBodilessEntity();
            status = "CREATED";
        } catch (RestClientException e) {
            status = "REJECTED";
        }
        Order saved = repository.save(new Order(request.sku(), request.quantity(), status));
        HttpStatus code = "CREATED".equals(status) ? HttpStatus.CREATED : HttpStatus.CONFLICT;
        return ResponseEntity.status(code).body(saved);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Order> get(@PathVariable Long id) {
        return repository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}
