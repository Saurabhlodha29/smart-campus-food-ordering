package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.EmailOtpToken;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

public interface EmailOtpTokenRepository extends JpaRepository<EmailOtpToken, Long> {

    /**
     * Finds the most recent unused, non-expired OTP for a given email.
     * Used during OTP verification.
     */
    @Query("""
            SELECT t FROM EmailOtpToken t
            WHERE t.email = :email
              AND t.used = false
              AND t.expiresAt > CURRENT_TIMESTAMP
            ORDER BY t.createdAt DESC
            """)
    List<EmailOtpToken> findValidTokens(String email);

    /**
     * Convenience default method: returns only the latest valid token.
     */
    default Optional<EmailOtpToken> findLatestValidToken(String email) {
        List<EmailOtpToken> tokens = findValidTokens(email);
        return tokens.isEmpty() ? Optional.empty() : Optional.of(tokens.get(0));
    }

    /**
     * Deletes ALL OTP tokens for an email before issuing a new one.
     * Used on resend-OTP requests to avoid stale tokens.
     */
    @Modifying
    @Transactional
    @Query("DELETE FROM EmailOtpToken t WHERE t.email = :email")
    void deleteAllByEmail(String email);
}