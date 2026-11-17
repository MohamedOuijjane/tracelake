package io.tracelake.orders;

import java.math.BigDecimal;
import java.time.Instant;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** A food order. The table is new, so volumes from the old sku based schema do not clash. */
@Entity
@Table(name = "food_orders")
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String restaurantId;

    /** Ordered dishes as JSON, for example [{"dish_id":"pz-margherita","quantity":2}]. */
    @Column(nullable = false, columnDefinition = "text")
    private String items;

    private String address;

    @Column(precision = 10, scale = 2)
    private BigDecimal total;

    private Integer preparationMinutes;

    private String paymentId;

    private String courierId;

    private Integer etaMinutes;

    @Column(nullable = false)
    private String status;

    @Column(nullable = false)
    private Instant createdAt = Instant.now();

    protected Order() {
    }

    public Order(String restaurantId, String items, String address, String status) {
        this.restaurantId = restaurantId;
        this.items = items;
        this.address = address;
        this.status = status;
    }

    public Long getId() {
        return id;
    }

    public String getRestaurantId() {
        return restaurantId;
    }

    public String getItems() {
        return items;
    }

    public String getAddress() {
        return address;
    }

    public BigDecimal getTotal() {
        return total;
    }

    public Integer getPreparationMinutes() {
        return preparationMinutes;
    }

    public String getPaymentId() {
        return paymentId;
    }

    public String getCourierId() {
        return courierId;
    }

    public Integer getEtaMinutes() {
        return etaMinutes;
    }

    public String getStatus() {
        return status;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    void priced(BigDecimal total, int preparationMinutes) {
        this.total = total;
        this.preparationMinutes = preparationMinutes;
    }

    void paid(String paymentId) {
        this.paymentId = paymentId;
    }

    void dispatched(String courierId, int etaMinutes) {
        this.courierId = courierId;
        this.etaMinutes = etaMinutes;
    }

    void status(String status) {
        this.status = status;
    }
}
