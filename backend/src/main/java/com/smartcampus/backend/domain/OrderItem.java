package com.smartcampus.backend.domain;

import jakarta.persistence.*;

@Entity
@Table(name = "order_items")
public class OrderItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id", nullable = false)
    private Order order;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "menu_item_id", nullable = false)
    private MenuItem menuItem;

    @Column(nullable = false)
    private int quantity;

    @Column(nullable = false)
    private double priceAtOrder;

    protected OrderItem() {
        // JPA only
    }

    public OrderItem(Order order, MenuItem menuItem, int quantity, double priceAtOrder) {
        this.order = order;
        this.menuItem = menuItem;
        this.quantity = quantity;
        this.priceAtOrder = priceAtOrder;
    }

    public Long getId() { return id; }
    public Order getOrder() { return order; }
    public MenuItem getMenuItem() { return menuItem; }
    public int getQuantity() { return quantity; }
    public double getPriceAtOrder() { return priceAtOrder; }
}