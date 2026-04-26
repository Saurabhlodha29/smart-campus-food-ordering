package com.smartcampus.backend.dto;

/**
 * Request body for {@code POST /api/penalties/{userId}/pay}.
 *
 * paymentMode: "ONLINE" | "CASH"
 */
public class PenaltyPaymentRequest {

    private String paymentMode;   // "ONLINE" | "CASH"

    public String getPaymentMode() {
        return paymentMode;
    }

    public void setPaymentMode(String paymentMode) {
        this.paymentMode = paymentMode;
    }
}