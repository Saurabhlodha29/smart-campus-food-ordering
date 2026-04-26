package com.smartcampus.backend.service;

import com.razorpay.RazorpayClient;
import com.razorpay.RazorpayException;
import com.razorpay.Utils;
import com.smartcampus.backend.domain.Order;
import com.smartcampus.backend.domain.Payment;
import com.smartcampus.backend.domain.User;
import com.smartcampus.backend.dto.PaymentInitResponse;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.OrderRepository;
import com.smartcampus.backend.repository.PaymentRepository;
import com.smartcampus.backend.repository.UserRepository;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.Map;

/**
 * Handles Razorpay payment creation and verification.
 *
 * <h3>Order payment flow (ONLINE)</h3>
 * <ol>
 * <li>Flutter calls POST /api/payments/initiate/order/{orderId}</li>
 * <li>Backend creates Razorpay order, returns rzpOrderId to Flutter</li>
 * <li>Flutter opens Razorpay checkout sheet</li>
 * <li>Student pays → Razorpay returns (rzpOrderId, rzpPaymentId,
 * signature)</li>
 * <li>Flutter calls POST /api/payments/verify/order</li>
 * <li>Backend verifies HMAC-SHA256 → marks order PAID → generates 4-digit
 * OTP</li>
 * <li>OTP is returned to Flutter so student can show it at pickup</li>
 * </ol>
 *
 * <h3>COD flow</h3>
 * OTP is generated at order creation in OrderService. No payment step here.
 *
 * <h3>Penalty payment flow</h3>
 * Same Razorpay flow but linked to a user's penalty amount.
 */
@Service
public class PaymentService {

    private static final Logger log = LoggerFactory.getLogger(PaymentService.class);

    private final RazorpayClient razorpayClient;
    private final PaymentRepository paymentRepo;
    private final OrderRepository orderRepo;
    private final UserRepository userRepo;

    @Value("${razorpay.key-id}")
    private String keyId;

    @Value("${razorpay.key-secret}")
    private String keySecret;

    public PaymentService(RazorpayClient razorpayClient,
            PaymentRepository paymentRepo,
            OrderRepository orderRepo,
            UserRepository userRepo) {
        this.razorpayClient = razorpayClient;
        this.paymentRepo = paymentRepo;
        this.orderRepo = orderRepo;
        this.userRepo = userRepo;
    }

    // ── ORDER PAYMENT ─────────────────────────────────────────────────────────

    @Transactional
    public PaymentInitResponse initiateOrderPayment(Long orderId) {

        Order order = orderRepo.findById(orderId)
                .orElseThrow(() -> new ApiException("Order not found: " + orderId, 404));

        if (!"ONLINE".equals(order.getPaymentMode())) {
            throw new ApiException(
                    "This is a COD order — no online payment needed. " +
                            "The student already has their OTP.",
                    400);
        }

        if ("PAID".equals(order.getPaymentStatus())) {
            throw new ApiException("Order is already paid.", 400);
        }

        // Return existing pending Razorpay order if one was already created
        if (paymentRepo.existsByOrderIdAndStatus(orderId, "CREATED")) {
            Payment existing = paymentRepo.findByOrderId(orderId).stream()
                    .filter(p -> "CREATED".equals(p.getStatus()))
                    .findFirst().orElseThrow();
            log.info("[PaymentService] Returning existing pending payment for order #{}", orderId);
            return new PaymentInitResponse(
                    existing.getRazorpayOrderId(), existing.getAmount(), existing.getCurrency(), keyId);
        }

        try {
            int amountInPaise = (int) Math.round(order.getTotalAmount() * 100);

            JSONObject orderRequest = new JSONObject();
            orderRequest.put("amount", amountInPaise);
            orderRequest.put("currency", "INR");
            orderRequest.put("receipt", "order_" + orderId);
            orderRequest.put("notes", new JSONObject()
                    .put("order_id", orderId.toString())
                    .put("type", "ORDER_PAYMENT"));

            com.razorpay.Order rzpOrder = razorpayClient.orders.create(orderRequest);
            String rzpOrderId = rzpOrder.get("id");

            Payment payment = new Payment(order, null, rzpOrderId,
                    order.getTotalAmount(), "ORDER_PAYMENT");
            paymentRepo.save(payment);

            log.info("[PaymentService] Razorpay order created: {} for order #{}", rzpOrderId, orderId);
            return new PaymentInitResponse(rzpOrderId, order.getTotalAmount(), "INR", keyId);

        } catch (RazorpayException e) {
            log.error("[PaymentService] Failed to create Razorpay order for order #{}: {}",
                    orderId, e.getMessage());
            throw new ApiException("Payment gateway error. Please try again.", 502);
        }
    }

    /**
     * Verifies Razorpay signature, marks order PAID, and generates the pickup OTP.
     *
     * @return the 4-digit OTP string — must be returned to Flutter so student can
     *         show it
     */
    @Transactional
    public String verifyOrderPayment(String rzpOrderId, String rzpPaymentId, String rzpSignature) {

        Payment payment = paymentRepo.findByRazorpayOrderId(rzpOrderId)
                .orElseThrow(() -> new ApiException(
                        "No payment record found for: " + rzpOrderId, 404));

        verifySignature(rzpOrderId, rzpPaymentId, rzpSignature);

        payment.setRazorpayPaymentId(rzpPaymentId);
        payment.setStatus("SUCCESS");
        paymentRepo.save(payment);

        // Mark order PAID and generate OTP
        Order order = payment.getOrder();
        order.setPaymentStatus("PAID");

        String otp = OrderService.generateOtp();
        order.setPickupOtp(otp);
        orderRepo.save(order);

        log.info("[PaymentService] Order #{} marked PAID. OTP generated. Razorpay: {}",
                order.getId(), rzpPaymentId);

        return otp;
    }

    @Transactional
    public String simulateOrderPayment(Long orderId) {
        Order order = orderRepo.findById(orderId)
                .orElseThrow(() -> new ApiException("Order not found: " + orderId, 404));

        if (!"ONLINE".equals(order.getPaymentMode())) {
            throw new ApiException("Only ONLINE orders can be simulated", 400);
        }

        Payment payment = new Payment(order, null, "rzp_test_" + orderId, order.getTotalAmount(), "ORDER_PAYMENT");
        payment.setRazorpayPaymentId("pay_test_" + orderId);
        payment.setStatus("SUCCESS");
        paymentRepo.save(payment);

        order.setPaymentStatus("PAID");
        String otp = OrderService.generateOtp();
        order.setPickupOtp(otp);
        orderRepo.save(order);

        log.info("[PaymentService] Order #{} marked PAID (SIMULATED). OTP generated.", order.getId());
        return otp;
    }

    // ── PENALTY PAYMENT ───────────────────────────────────────────────────────

    @Transactional
    public PaymentInitResponse initiatePenaltyPayment(Long userId) {

        User user = userRepo.findById(userId)
                .orElseThrow(() -> new ApiException("User not found: " + userId, 404));

        double pendingAmount = user.getPendingPenaltyAmount();
        if (pendingAmount <= 0) {
            throw new ApiException("No outstanding penalty for this user.", 400);
        }

        boolean existingPending = paymentRepo.findByPenaltyUserId(userId).stream()
                .anyMatch(p -> "CREATED".equals(p.getStatus()));
        if (existingPending) {
            Payment existing = paymentRepo.findByPenaltyUserId(userId).stream()
                    .filter(p -> "CREATED".equals(p.getStatus()))
                    .findFirst().orElseThrow();
            return new PaymentInitResponse(
                    existing.getRazorpayOrderId(), existing.getAmount(), existing.getCurrency(), keyId);
        }

        try {
            int amountInPaise = (int) Math.round(pendingAmount * 100);

            JSONObject orderRequest = new JSONObject();
            orderRequest.put("amount", amountInPaise);
            orderRequest.put("currency", "INR");
            orderRequest.put("receipt", "penalty_" + userId);
            orderRequest.put("notes", new JSONObject()
                    .put("user_id", userId.toString())
                    .put("type", "PENALTY_PAYMENT"));

            com.razorpay.Order rzpOrder = razorpayClient.orders.create(orderRequest);
            String rzpOrderId = rzpOrder.get("id");

            Payment payment = new Payment(null, userId, rzpOrderId, pendingAmount, "PENALTY_PAYMENT");
            paymentRepo.save(payment);

            log.info("[PaymentService] Penalty payment initiated for user #{}: ₹{}", userId, pendingAmount);
            return new PaymentInitResponse(rzpOrderId, pendingAmount, "INR", keyId);

        } catch (RazorpayException e) {
            log.error("[PaymentService] Razorpay order creation failed for penalty userId={}: {}",
                    userId, e.getMessage());
            throw new ApiException("Payment gateway error. Please try again.", 502);
        }
    }

    @Transactional
    public void verifyPenaltyPayment(String rzpOrderId, String rzpPaymentId, String rzpSignature) {

        Payment payment = paymentRepo.findByRazorpayOrderId(rzpOrderId)
                .orElseThrow(() -> new ApiException(
                        "No payment record found for: " + rzpOrderId, 404));

        verifySignature(rzpOrderId, rzpPaymentId, rzpSignature);

        payment.setRazorpayPaymentId(rzpPaymentId);
        payment.setStatus("SUCCESS");
        paymentRepo.save(payment);

        Long userId = payment.getPenaltyUserId();
        User user = userRepo.findById(userId)
                .orElseThrow(() -> new ApiException("User not found: " + userId, 404));

        double cleared = user.getPendingPenaltyAmount();
        user.setPendingPenaltyAmount(0.0);
        if ("WARNING".equals(user.getAccountStatus())) {
            user.setAccountStatus("ACTIVE");
        }
        userRepo.save(user);

        log.info("[PaymentService] Penalty cleared for user #{}: ₹{} via {}", userId, cleared, rzpPaymentId);
    }

    // ── REFUND (cancelled paid online orders) ────────────────────────────────

    /**
     * Initiates a Razorpay refund for an order that was paid online and then
     * cancelled by the student (paymentStatus = REFUND_PENDING).
     *
     * Called by Admin via POST /api/payments/refund/order/{orderId}.
     * In Razorpay test mode refunds are instant; in live mode 5-7 business days.
     */
    @Transactional
    public Map<String, Object> processOrderRefund(Long orderId) {

        Order order = orderRepo.findById(orderId)
                .orElseThrow(() -> new ApiException("Order not found: " + orderId, 404));

        if (!"REFUND_PENDING".equals(order.getPaymentStatus())) {
            throw new ApiException(
                    "Order is not in REFUND_PENDING state. Current paymentStatus: "
                            + order.getPaymentStatus(),
                    400);
        }

        // Find the captured payment for this order
        Payment payment = paymentRepo.findByOrderId(orderId).stream()
                .filter(p -> "CAPTURED".equals(p.getStatus()) || "SUCCESS".equals(p.getStatus()))
                .findFirst()
                .orElseThrow(() -> new ApiException(
                        "No captured payment found for order #" + orderId
                                + ". Cannot initiate refund.",
                        404));

        try {
            int amountInPaise = (int) Math.round(order.getTotalAmount() * 100);

            JSONObject refundRequest = new JSONObject();
            refundRequest.put("amount", amountInPaise);
            refundRequest.put("speed", "normal");
            refundRequest.put("notes", new JSONObject()
                    .put("reason", "Order cancelled by student")
                    .put("order_id", String.valueOf(orderId)));

            com.razorpay.Refund refund = razorpayClient.payments.refund(
                    payment.getRazorpayPaymentId(), refundRequest);

            order.setPaymentStatus("REFUND_INITIATED");
            orderRepo.save(order);

            log.info("[PaymentService] Refund initiated for order #{}: refundId={}, amount=₹{}",
                    orderId, refund.get("id"), order.getTotalAmount());

            return Map.of(
                    "message", "Refund initiated successfully",
                    "refundId", refund.get("id").toString(),
                    "amount", order.getTotalAmount(),
                    "orderId", orderId,
                    "status", "REFUND_INITIATED");

        } catch (RazorpayException e) {
            log.error("[PaymentService] Razorpay refund failed for order #{}: {}", orderId, e.getMessage());
            throw new ApiException("Razorpay refund failed: " + e.getMessage(), 500);
        }
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private void verifySignature(String rzpOrderId, String rzpPaymentId, String rzpSignature) {
        try {
            JSONObject attributes = new JSONObject();
            attributes.put("razorpay_order_id", rzpOrderId);
            attributes.put("razorpay_payment_id", rzpPaymentId);
            attributes.put("razorpay_signature", rzpSignature);

            boolean valid = Utils.verifyPaymentSignature(attributes, keySecret);
            if (!valid) {
                log.warn("[PaymentService] Signature mismatch for rzpOrderId={}", rzpOrderId);
                throw new ApiException("Payment verification failed — invalid signature.", 400);
            }
        } catch (RazorpayException e) {
            log.error("[PaymentService] Signature verification error: {}", e.getMessage());
            throw new ApiException("Payment verification error.", 400);
        }
    }
}