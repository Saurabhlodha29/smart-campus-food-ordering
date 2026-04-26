package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.Payment;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface PaymentRepository extends JpaRepository<Payment, Long> {

    Optional<Payment> findByRazorpayOrderId(String razorpayOrderId);

    List<Payment> findByOrderId(Long orderId);

    List<Payment> findByPenaltyUserId(Long userId);

    /**
     * Idempotency check: did this user already create a PENDING/CREATED penalty
     * payment?
     */
    Optional<Payment> findByPenaltyUserIdAndStatus(Long userId, String status);

    boolean existsByOrderIdAndStatus(Long orderId, String status);
}