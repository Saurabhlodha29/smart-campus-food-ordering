package com.smartcampus.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

/**
 * Sent by the MANAGER when a student presents their 4-digit OTP at pickup.
 *
 * <pre>
 * POST /api/orders/{orderId}/pickup
 * Body: { "otp": "4729" }
 * </pre>
 */
public class OtpRequest {

    @NotBlank(message = "OTP is required")
    @Pattern(regexp = "\\d{4}", message = "OTP must be exactly 4 digits")
    private String otp;

    public String getOtp() { return otp; }
    public void setOtp(String otp) { this.otp = otp; }
}