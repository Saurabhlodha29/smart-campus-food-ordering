package com.smartcampus.backend.domain;

import jakarta.persistence.*;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.time.LocalDateTime;

@JsonIgnoreProperties({ "hibernateLazyInitializer", "handler" })
@Entity
@Table(name = "orders")
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "student_id", nullable = true)
    private User student;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "outlet_id", nullable = false)
    private Outlet outlet;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "pickup_slot_id", nullable = true)
    private PickupSlot pickupSlot;

    @Column(nullable = false, length = 30)
    private String status;
    // PLACED, PREPARING, READY, PICKED, EXPIRED, CANCELLED

    @Column(nullable = false)
    private double totalAmount;

    @Column(nullable = false, length = 20)
    private String paymentMode;
    // ONLINE, CASH

    @Column(nullable = false, length = 20)
    private String paymentStatus;
    // PENDING, PAID, FAILED

    // Smart predicted completion time
    @Column(nullable = false)
    private LocalDateTime readyAt;

    // Grace expiry time (readyAt + 30 mins)
    @Column(nullable = false)
    private LocalDateTime expiresAt;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    /**
     * 4-digit OTP generated at order creation (COD) or at payment verification
     * (ONLINE).
     * Student shows this to the manager at pickup.
     * Manager submits it via POST /api/orders/{id}/pickup to mark the order PICKED.
     * Stored as a String to preserve any leading zeros (e.g. "0472").
     */
    @Column(length = 4)
    private String pickupOtp;

    /**
     * Source of the order:
     * "PLATFORM" = placed by student via app (normal flow)
     * "COUNTER" = placed by manager at the counter for a walk-in customer
     */
    @Column(name = "order_source", nullable = false, length = 10)
    private String orderSource = "PLATFORM";

    /**
     * For COUNTER orders: the walk-in customer's name typed by the manager.
     * Null for PLATFORM orders (student name is in the student relation).
     */
    @Column(length = 120)
    private String customerName;

    protected Order() {
    }

    public Order(User student,
            Outlet outlet,
            PickupSlot pickupSlot,
            String status,
            double totalAmount,
            String paymentMode,
            String paymentStatus,
            LocalDateTime readyAt,
            LocalDateTime expiresAt) {

        this.student = student;
        this.outlet = outlet;
        this.pickupSlot = pickupSlot;
        this.status = status;
        this.totalAmount = totalAmount;
        this.paymentMode = paymentMode;
        this.paymentStatus = paymentStatus;
        this.readyAt = readyAt;
        this.expiresAt = expiresAt;
        this.createdAt = LocalDateTime.now();
    }

    // ── Getters ───────────────────────────────────────────────────────────────
    public Long getId() {
        return id;
    }

    public User getStudent() {
        return student;
    }

    public Outlet getOutlet() {
        return outlet;
    }

    public PickupSlot getPickupSlot() {
        return pickupSlot;
    }

    public String getStatus() {
        return status;
    }

    public double getTotalAmount() {
        return totalAmount;
    }

    public String getPaymentMode() {
        return paymentMode;
    }

    public String getPaymentStatus() {
        return paymentStatus;
    }

    public LocalDateTime getReadyAt() {
        return readyAt;
    }

    public LocalDateTime getExpiresAt() {
        return expiresAt;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public String getPickupOtp() {
        return pickupOtp;
    }

    public String getOrderSource() {
        return orderSource;
    }

    public String getCustomerName() {
        return customerName;
    }

    // ── Setters ───────────────────────────────────────────────────────────────
    public void setPickupSlot(PickupSlot slot) {
        this.pickupSlot = slot;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public void setPaymentStatus(String ps) {
        this.paymentStatus = ps;
    }

    public void setPickupOtp(String pickupOtp) {
        this.pickupOtp = pickupOtp;
    }

    public void setOrderSource(String orderSource) {
        this.orderSource = orderSource;
    }

    public void setCustomerName(String n) {
        this.customerName = n;
    }
}