package com.smartcampus.backend.service;

import com.smartcampus.backend.domain.EmailOtpToken;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.EmailOtpTokenRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.time.LocalDateTime;

/**
 * Manages OTP generation, storage, and validation for email verification.
 *
 * Uses SecureRandom (cryptographically strong) instead of Math.random()
 * to generate OTPs — important for security.
 */
@Service
public class OtpService {

    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    @Value("${otp.expiry-minutes:10}")
    private int otpExpiryMinutes;

    private final EmailOtpTokenRepository otpTokenRepo;
    private final EmailService emailService;

    public OtpService(EmailOtpTokenRepository otpTokenRepo, EmailService emailService) {
        this.otpTokenRepo = otpTokenRepo;
        this.emailService = emailService;
    }

    /**
     * Generates a new 6-digit OTP, saves it to the DB, and emails it.
     * Any existing OTPs for this email are deleted first.
     *
     * @param email    The recipient's email address
     * @param fullName The user's name for personalising the email
     */
    @Transactional
    public void generateAndSendOtp(String email, String fullName) {
        // Delete any old OTPs for this email (handles resend scenario)
        otpTokenRepo.deleteAllByEmail(email);

        // Generate a cryptographically secure 6-digit OTP
        String otp = String.format("%06d", SECURE_RANDOM.nextInt(1_000_000));

        // Save to DB with expiry timestamp
        LocalDateTime expiresAt = LocalDateTime.now().plusMinutes(otpExpiryMinutes);
        EmailOtpToken token = new EmailOtpToken(email, otp, expiresAt);
        otpTokenRepo.save(token);

        // Trigger async email
        System.out.println("DEBUG OTP GENERATED: " + otp);
        emailService.sendOtpEmail(email, fullName, otp);
    }

    /**
     * Validates the OTP submitted by the user.
     *
     * Checks:
     * 1. A valid (unused + non-expired) token exists for this email
     * 2. The submitted OTP matches the stored one
     * 3. Marks the token as used on success
     *
     * @param email        The email being verified
     * @param submittedOtp The OTP entered by the user
     * @throws ApiException if OTP is invalid or expired
     */
    @Transactional
    public void validateOtp(String email, String submittedOtp) {
        EmailOtpToken token = otpTokenRepo.findLatestValidToken(email)
                .orElseThrow(() -> new ApiException(
                        "OTP expired or not found. Please request a new one.", 400));

        if (!token.getOtpCode().equals(submittedOtp)) {
            throw new ApiException("Invalid OTP. Please check and try again.", 400);
        }

        token.markUsed();
        otpTokenRepo.save(token);
    }
}