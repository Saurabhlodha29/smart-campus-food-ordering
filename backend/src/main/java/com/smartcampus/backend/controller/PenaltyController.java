package com.smartcampus.backend.controller;

import com.smartcampus.backend.domain.User;
import com.smartcampus.backend.dto.PenaltyPaymentRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.UserRepository;
import com.smartcampus.backend.service.MLClient;
import jakarta.transaction.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Penalty status, waive, and legacy cash-payment APIs.
 *
 * <pre>
 * GET   /api/penalties/{userId}/status   Check current penalty status (any authenticated user)
 * POST  /api/penalties/{userId}/pay      DEPRECATED for ONLINE — use /api/payments/initiate/penalty/{userId}
 *                                         Still works for CASH payments.
 * POST  /api/penalties/{userId}/waive    Admin: waive penalty without payment
 * GET   /api/penalties/ml-health         Ops: check ML service reachability
 * </pre>
 *
 * Security: all endpoints require a valid JWT (anyRequest().authenticated() in SecurityConfig).
 */
@RestController
@RequestMapping("/api/penalties")
public class PenaltyController {

    private final UserRepository userRepository;
    private final MLClient       mlClient;

    public PenaltyController(UserRepository userRepository,
                             MLClient       mlClient) {
        this.userRepository = userRepository;
        this.mlClient       = mlClient;
    }

    // ── Penalty status ────────────────────────────────────────────────────────

    /**
     * Get the current penalty status for a user.
     *
     * <pre>
     * GET /api/penalties/{userId}/status
     *
     * Response:
     * {
     *   "userId":               1,
     *   "fullName":             "Saurabh Lodha",
     *   "email":                "saurabh@bennett.edu.in",
     *   "noShowCount":          2,
     *   "pendingPenaltyAmount": 25.00,
     *   "accountStatus":        "WARNING"
     * }
     * </pre>
     */
    @GetMapping("/{userId}/status")
    public Map<String, Object> getPenaltyStatus(@PathVariable Long userId) {

        User user = findUser(userId);

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("userId",               userId);
        response.put("fullName",             user.getFullName());
        response.put("email",                user.getEmail());
        response.put("noShowCount",          user.getNoShowCount());
        response.put("pendingPenaltyAmount", user.getPendingPenaltyAmount());
        response.put("accountStatus",        user.getAccountStatus());
        return response;
    }

    /**
     * Convenience endpoint — returns the calling user's own penalty status
     * without needing to know their userId.
     *
     * <pre>
     * GET /api/penalties/me
     * </pre>
     */
    @GetMapping("/me")
    public Map<String, Object> getMyPenaltyStatus() {
        String email = org.springframework.security.core.context.SecurityContextHolder
                .getContext().getAuthentication().getName();
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", 404));

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("userId",               user.getId());
        response.put("fullName",             user.getFullName());
        response.put("email",                user.getEmail());
        response.put("noShowCount",          user.getNoShowCount());
        response.put("pendingPenaltyAmount", user.getPendingPenaltyAmount());
        response.put("accountStatus",        user.getAccountStatus());
        return response;
    }

    // ── Pay penalty ───────────────────────────────────────────────────────────

    /**
     * Pay an outstanding penalty.
     *
     * <p><strong>ONLINE payments are deprecated here.</strong>
     * Flutter should call {@code POST /api/payments/initiate/penalty/{userId}} instead,
     * which opens the Razorpay checkout sheet and verifies the HMAC signature.
     * This endpoint still accepts {@code paymentMode=CASH} for cash desk payments
     * handled by an admin or manager.
     *
     * <pre>
     * POST /api/penalties/{userId}/pay
     * Body: { "paymentMode": "CASH" }
     * </pre>
     */
    @PostMapping("/{userId}/pay")
    @Transactional
    public Map<String, Object> payPenalty(
            @PathVariable Long userId,
            @RequestBody  PenaltyPaymentRequest req) {

        User user = findUser(userId);

        double pendingAmount = user.getPendingPenaltyAmount();
        if (pendingAmount <= 0) {
            throw new ApiException("No outstanding penalty for this user.", 400);
        }

        String paymentMode = req.getPaymentMode();
        if (paymentMode == null || (!paymentMode.equals("ONLINE") && !paymentMode.equals("CASH"))) {
            throw new ApiException("paymentMode must be ONLINE or CASH.", 400);
        }

        // Redirect ONLINE to the Razorpay flow — don't silently zero out the DB.
        if ("ONLINE".equals(paymentMode)) {
            throw new ApiException(
                "ONLINE penalty payment must go through the Razorpay flow. " +
                "Call POST /api/payments/initiate/penalty/" + userId + " instead.", 400);
        }

        // CASH path: admin/manager confirms physical cash received — clear immediately.
        user.setPendingPenaltyAmount(0.0);
        if ("WARNING".equals(user.getAccountStatus())) {
            user.setAccountStatus("ACTIVE");
        }
        userRepository.save(user);

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("userId",           userId);
        response.put("clearedAmount",    pendingAmount);
        response.put("newPendingAmount", 0.0);
        response.put("newAccountStatus", user.getAccountStatus());
        response.put("paymentMode",      paymentMode);
        response.put("paidAt",           LocalDateTime.now().toString());
        response.put("message",
                String.format("Penalty of ₹%.2f cleared via CASH.", pendingAmount));

        return response;
    }

    // ── Waive penalty ─────────────────────────────────────────────────────────

    /**
     * Admin waives a student's penalty without payment (e.g. emergency, system error).
     *
     * <pre>
     * POST /api/penalties/{userId}/waive
     * (no body required)
     * </pre>
     */
    @PostMapping("/{userId}/waive")
    @Transactional
    public Map<String, Object> waivePenalty(@PathVariable Long userId) {

        User user = findUser(userId);

        double waivedAmount = user.getPendingPenaltyAmount();
        user.setPendingPenaltyAmount(0.0);

        if ("WARNING".equals(user.getAccountStatus())) {
            user.setAccountStatus("ACTIVE");
        }

        userRepository.save(user);

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("userId",           userId);
        response.put("waivedAmount",     waivedAmount);
        response.put("newPendingAmount", 0.0);
        response.put("newAccountStatus", user.getAccountStatus());
        response.put("waivedAt",         LocalDateTime.now().toString());
        response.put("message",
                String.format("Penalty of ₹%.2f waived by admin.", waivedAmount));

        return response;
    }

    // ── ML health check ───────────────────────────────────────────────────────

    /**
     * Quick ops check — is the Python ML microservice reachable?
     *
     * <pre>
     * GET /api/penalties/ml-health
     * </pre>
     */
    @GetMapping("/ml-health")
    public Map<String, Object> mlHealth() {
        boolean reachable = mlClient.isHealthy();
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("mlServiceReachable", reachable);
        response.put("checkedAt", LocalDateTime.now().toString());
        return response;
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private User findUser(Long userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new ApiException("User not found: " + userId, 404));
    }
}