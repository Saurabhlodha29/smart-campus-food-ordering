package com.smartcampus.backend.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

/**
 * Used by POST /api/auth/verify-email.
 * Sent after registration to submit the 6-digit OTP.
 */
public class VerifyEmailRequest {

    @NotBlank(message = "Email is required")
    @Email(message = "Must be a valid email")
    private String email;

    @NotBlank(message = "OTP is required")
    @Pattern(regexp = "\\d{6}", message = "OTP must be exactly 6 digits")
    private String otp;

    public String getEmail() {
        return email;
    }

    public void setEmail(String v) {
        this.email = v;
    }

    public String getOtp() {
        return otp;
    }

    public void setOtp(String v) {
        this.otp = v;
    }
}