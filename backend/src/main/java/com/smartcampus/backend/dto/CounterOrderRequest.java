package com.smartcampus.backend.dto;

import java.util.List;

/**
 * DTO for a manager-placed counter (walk-in) order.
 * No studentId, no slotId — these are anonymous or named customers.
 */
public class CounterOrderRequest {

    /** Name of the walk-in customer (e.g. "Parent - Sharma"). Optional. */
    private String customerName;

    /**
     * Payment mode: "CASH" or "ONLINE"
     * For ONLINE: manager scans QR / takes UPI reference from customer directly.
     */
    private String paymentMode;

    /** Items being ordered */
    private List<OrderItemRequest> items;

    /**
     * Optional: if the manager wants to associate this with a slot
     * (e.g. a registered student forgot to order via app).
     * If null, no slot count is incremented.
     */
    private Long slotId;

    // Getters and Setters
    public String getCustomerName() {
        return customerName;
    }

    public void setCustomerName(String customerName) {
        this.customerName = customerName;
    }

    public String getPaymentMode() {
        return paymentMode;
    }

    public void setPaymentMode(String paymentMode) {
        this.paymentMode = paymentMode;
    }

    public List<OrderItemRequest> getItems() {
        return items;
    }

    public void setItems(List<OrderItemRequest> items) {
        this.items = items;
    }

    public Long getSlotId() {
        return slotId;
    }

    public void setSlotId(Long slotId) {
        this.slotId = slotId;
    }
}