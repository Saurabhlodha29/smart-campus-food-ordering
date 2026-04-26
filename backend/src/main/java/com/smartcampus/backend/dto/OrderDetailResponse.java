package com.smartcampus.backend.dto;

import com.smartcampus.backend.domain.Order;
import java.time.LocalDateTime;
import java.util.List;

public class OrderDetailResponse {
    private Long id;
    private String status;
    private double totalAmount;
    private String paymentMode;
    private String paymentStatus;
    private LocalDateTime readyAt;
    private LocalDateTime expiresAt;
    private LocalDateTime createdAt;
    private String pickupOtp;
    private String orderSource;
    private String customerName;
    private Long outletId;
    private String outletName;
    private Long studentId;
    private String studentName;
    private List<OrderItemResponse> items;

    public OrderDetailResponse(Order order, List<OrderItemResponse> items) {
        this.id = order.getId();
        this.status = order.getStatus();
        this.totalAmount = order.getTotalAmount();
        this.paymentMode = order.getPaymentMode();
        this.paymentStatus = order.getPaymentStatus();
        this.readyAt = order.getReadyAt();
        this.expiresAt = order.getExpiresAt();
        this.createdAt = order.getCreatedAt();
        this.pickupOtp = order.getPickupOtp();
        this.orderSource = order.getOrderSource();
        this.customerName = order.getCustomerName();
        this.outletId = order.getOutlet().getId();
        this.outletName = order.getOutlet().getName();
        if (order.getStudent() != null) {
            this.studentId = order.getStudent().getId();
            this.studentName = order.getStudent().getFullName();
        }
        this.items = items;
    }

    public Long getId()               { return id; }
    public String getStatus()         { return status; }
    public double getTotalAmount()    { return totalAmount; }
    public String getPaymentMode()    { return paymentMode; }
    public String getPaymentStatus()  { return paymentStatus; }
    public LocalDateTime getReadyAt() { return readyAt; }
    public LocalDateTime getExpiresAt() { return expiresAt; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public String getPickupOtp()      { return pickupOtp; }
    public String getOrderSource()    { return orderSource; }
    public String getCustomerName()   { return customerName; }
    public Long getOutletId()         { return outletId; }
    public String getOutletName()     { return outletName; }
    public Long getStudentId()        { return studentId; }
    public String getStudentName()    { return studentName; }
    public List<OrderItemResponse> getItems() { return items; }
}
