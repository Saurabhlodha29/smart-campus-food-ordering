package com.smartcampus.backend.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

/**
 * Tracks every Razorpay payment attempt — for both order payments and penalty payments.
 *
 * <p>Lifecycle:
 * <pre>
 *   CREATED  → (student pays on Flutter) → SUCCESS
 *            → (payment fails/timeout)   → FAILED
 *   SUCCESS  → (refund initiated)        → REFUNDED  (future use)
 * </pre>
 *
 * <p>One order has at most one successful Payment record.
 * A penalty payment is linked via {@code penaltyUserId} (no separate Penalty entity yet).
 */
@Entity
@Table(name = "payments")
public class Payment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * Linked order — null when this is a penalty payment.
     */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id")
    private Order order;

    /**
     * Set when this is a penalty payment — holds the student's user ID.
     * Null for order payments.
     */
    @Column(name = "penalty_user_id")
    private Long penaltyUserId;

    /**
     * rzp_order_XXXX — created by us via Razorpay Orders API before checkout opens.
     */
    @Column(nullable = false, unique = true, length = 100)
    private String razorpayOrderId;

    /**
     * pay_XXXX — returned by Razorpay after the student successfully pays.
     * Null until payment is verified.
     */
    @Column(length = 100)
    private String razorpayPaymentId;

    @Column(nullable = false)
    private double amount;

    @Column(nullable = false, length = 10)
    private String currency = "INR";

    /**
     * ORDER_PAYMENT | PENALTY_PAYMENT
     */
    @Column(nullable = false, length = 20)
    private String type;

    /**
     * CREATED | SUCCESS | FAILED | REFUNDED
     */
    @Column(nullable = false, length = 20)
    private String status;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @Column
    private LocalDateTime updatedAt;

    protected Payment() {}

    public Payment(Order order, Long penaltyUserId, String razorpayOrderId,
                   double amount, String type) {
        this.order           = order;
        this.penaltyUserId   = penaltyUserId;
        this.razorpayOrderId = razorpayOrderId;
        this.amount          = amount;
        this.type            = type;
        this.status          = "CREATED";
        this.createdAt       = LocalDateTime.now();
    }

    // ── Getters ───────────────────────────────────────────────────────────────

    public Long          getId()               { return id; }
    public Order         getOrder()            { return order; }
    public Long          getPenaltyUserId()    { return penaltyUserId; }
    public String        getRazorpayOrderId()  { return razorpayOrderId; }
    public String        getRazorpayPaymentId(){ return razorpayPaymentId; }
    public double        getAmount()           { return amount; }
    public String        getCurrency()         { return currency; }
    public String        getType()             { return type; }
    public String        getStatus()           { return status; }
    public LocalDateTime getCreatedAt()        { return createdAt; }
    public LocalDateTime getUpdatedAt()        { return updatedAt; }

    // ── Setters ───────────────────────────────────────────────────────────────

    public void setRazorpayPaymentId(String razorpayPaymentId) {
        this.razorpayPaymentId = razorpayPaymentId;
    }

    public void setStatus(String status) {
        this.status    = status;
        this.updatedAt = LocalDateTime.now();
    }
}