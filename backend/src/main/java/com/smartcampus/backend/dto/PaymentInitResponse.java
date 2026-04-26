package com.smartcampus.backend.dto;

/**
 * Returned to Flutter after a Razorpay order is created.
 * Flutter uses these fields to open the Razorpay checkout sheet.
 */
public class PaymentInitResponse {

    private String razorpayOrderId;   // rzp_order_XXXX
    private double amount;            // in INR (NOT paise — Flutter converts)
    private String currency;
    private String keyId;             // Razorpay public key — safe to send to client

    public PaymentInitResponse(String razorpayOrderId, double amount,
                                String currency, String keyId) {
        this.razorpayOrderId = razorpayOrderId;
        this.amount          = amount;
        this.currency        = currency;
        this.keyId           = keyId;
    }

    public String getRazorpayOrderId() { return razorpayOrderId; }
    public double getAmount()          { return amount; }
    public String getCurrency()        { return currency; }
    public String getKeyId()           { return keyId; }
}