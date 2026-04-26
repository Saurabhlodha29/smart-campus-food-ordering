package com.smartcampus.backend.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

/**
 * Stores the 6-digit email verification OTP for new user registration.
 *
 * Lifecycle:
 * 1. Created when user registers → status = PENDING
 * 2. Consumed when user submits correct OTP → status = USED (account activated)
 * 3. Expires if not used within otp.expiry-minutes → status checked at verify
 * time
 *
 * One active OTP per email at a time. If user requests a resend,
 * old tokens for that email are deleted and a new one is created.
 */
@Entity
@Table(name = "email_otp_tokens")
public class EmailOtpToken {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 150)
    private String email;

    @Column(nullable = false, length = 6)
    private String otpCode;

    @Column(nullable = false)
    private LocalDateTime expiresAt;

    @Column(nullable = false)
    private boolean used = false;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    protected EmailOtpToken() {
    }

    public EmailOtpToken(String email, String otpCode, LocalDateTime expiresAt) {
        this.email = email;
        this.otpCode = otpCode;
        this.expiresAt = expiresAt;
        this.createdAt = LocalDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public String getEmail() {
        return email;
    }

    public String getOtpCode() {
        return otpCode;
    }

    public LocalDateTime getExpiresAt() {
        return expiresAt;
    }

    public boolean isUsed() {
        return used;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void markUsed() {
        this.used = true;
    }
}