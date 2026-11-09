package io.tracelake.gateway;

import java.util.List;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import reactor.core.publisher.Mono;

/** Product catalog served at the edge. Used by the "browse" load scenario. */
@RestController
@RequestMapping("/api/catalog")
public class CatalogController {

    public record Product(String sku, String name, double price) {}

    private static final List<Product> PRODUCTS = List.of(
            new Product("SKU-001", "Keyboard", 49.90),
            new Product("SKU-002", "Mouse", 19.90),
            new Product("SKU-003", "Monitor", 189.00),
            new Product("SKU-004", "Headset", 79.50));

    @GetMapping
    public Mono<List<Product>> list() {
        return Mono.just(PRODUCTS);
    }
}
