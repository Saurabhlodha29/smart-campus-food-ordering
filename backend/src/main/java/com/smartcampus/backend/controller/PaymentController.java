package com.smartcampus.backend.controller;

import com.smartcampus.backend.dto.PaymentInitResponse;
import com.smartcampus.backend.dto.PaymentVerifyRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.PaymentRepository;
import com.smartcampus.backend.service.PaymentService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Payment endpoints.
 *
 * <pre>
 * POST  /api/payments/initiate/order/{orderId}     STUDENT  — get Razorpay order for checkout
 * POST  /api/payments/verify/order                 STUDENT  — confirm payment, receive OTP
 * POST  /api/payments/initiate/penalty/{userId}    STUDENT  — get Razorpay order for penalty
 * POST  /api/payments/verify/penalty               STUDENT  — confirm penalty payment
 * GET   /api/payments/order/{orderId}              Authenticated — payment history for an order
 * </pre>
 */
@RestController
@RequestMapping("/api/payments")
public class PaymentController {

    private final PaymentService paymentService;
    private final PaymentRepository paymentRepo;

    public PaymentController(PaymentService paymentService,
            PaymentRepository paymentRepo) {
        this.paymentService = paymentService;
        this.paymentRepo = paymentRepo;
    }

    // ── ORDER PAYMENT ─────────────────────────────────────────────────────────

    @PostMapping("/initiate/order/{orderId}")
    public PaymentInitResponse initiateOrderPayment(@PathVariable Long orderId) {
        return paymentService.initiateOrderPayment(orderId);
    }

    /**
     * Verifies Razorpay payment signature and returns the 4-digit pickup OTP.
     *
     * <pre>
     * Response:
     * {
     *   "success":    true,
     *   "message":    "Payment verified. Your order is confirmed.",
     *   "pickupOtp":  "4729",       ← show this to the manager at pickup
     *   "verifiedAt": "2026-04-12T..."
     * }
     * </pre>
     */
    @PostMapping("/verify/order")
    public Map<String, Object> verifyOrderPayment(@Valid @RequestBody PaymentVerifyRequest req) {

        String otp = paymentService.verifyOrderPayment(
                req.getRazorpayOrderId(),
                req.getRazorpayPaymentId(),
                req.getRazorpaySignature());

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("success", true);
        response.put("message", "Payment verified. Your order is confirmed.");
        response.put("pickupOtp", otp);
        response.put("verifiedAt", LocalDateTime.now().toString());
        return response;
    }

    @PostMapping("/order/{orderId}/simulate")
    public Map<String, Object> simulatePayment(@PathVariable Long orderId, @RequestBody Map<String, Boolean> body) {
        if (!Boolean.TRUE.equals(body.get("success"))) {
            throw new ApiException("Simulation failed intentionally", 400);
        }
        String otp = paymentService.simulateOrderPayment(orderId);
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("success", true);
        response.put("message", "Payment simulated. Your order is confirmed.");
        response.put("pickupOtp", otp);
        response.put("verifiedAt", LocalDateTime.now().toString());
        return response;
    }

    // ── PENALTY PAYMENT ───────────────────────────────────────────────────────

    @PostMapping("/initiate/penalty/{userId}")
    public PaymentInitResponse initiatePenaltyPayment(@PathVariable Long userId) {
        return paymentService.initiatePenaltyPayment(userId);
    }

    @PostMapping("/verify/penalty")
    public Map<String, Object> verifyPenaltyPayment(@Valid @RequestBody PaymentVerifyRequest req) {

        paymentService.verifyPenaltyPayment(
                req.getRazorpayOrderId(),
                req.getRazorpayPaymentId(),
                req.getRazorpaySignature());

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("success", true);
        response.put("message", "Penalty payment verified. Your account has been restored.");
        response.put("verifiedAt", LocalDateTime.now().toString());
        return response;
    }

    /**
     * POST /api/payments/refund/order/{orderId}
     * Admin-triggered refund for a REFUND_PENDING order.
     * In production you'd also call this from a webhook or a scheduled job.
     */
    @PostMapping("/refund/order/{orderId}")
    public Map<String, Object> refundOrder(@PathVariable Long orderId) {
        return paymentService.processOrderRefund(orderId);
    }

    // ── READ ──────────────────────────────────────────────────────────────────

    @GetMapping("/order/{orderId}")
    public Object getPaymentsForOrder(@PathVariable Long orderId) {
        return paymentRepo.findByOrderId(orderId);
    }
}