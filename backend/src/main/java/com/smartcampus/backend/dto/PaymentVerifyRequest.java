package com.smartcampus.backend.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * Sent by Flutter after the Razorpay checkout sheet completes successfully.
 * All three fields are required for signature verification.
 */
public class PaymentVerifyRequest {

    @NotBlank
    private String razorpayOrderId;    // rzp_order_XXXX — from your initiate call

    @NotBlank
    private String razorpayPaymentId;  // pay_XXXX — from Razorpay callback

    @NotBlank
    private String razorpaySignature;  // HMAC-SHA256 — from Razorpay callback

    public String getRazorpayOrderId()   { return razorpayOrderId; }
    public String getRazorpayPaymentId() { return razorpayPaymentId; }
    public String getRazorpaySignature() { return razorpaySignature; }

    public void setRazorpayOrderId(String razorpayOrderId) {
        this.razorpayOrderId = razorpayOrderId;
    }
    public void setRazorpayPaymentId(String razorpayPaymentId) {
        this.razorpayPaymentId = razorpayPaymentId;
    }
    public void setRazorpaySignature(String razorpaySignature) {
        this.razorpaySignature = razorpaySignature;
    }
}