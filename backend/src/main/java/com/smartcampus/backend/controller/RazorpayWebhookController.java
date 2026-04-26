package com.smartcampus.backend.controller;

import com.smartcampus.backend.domain.OutletPayout;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.OutletPayoutRepository;
import jakarta.servlet.http.HttpServletRequest;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.HexFormat;
import java.util.Map;

/**
 * Receives and authenticates Razorpay server-to-server webhook events.
 *
 * <p><strong>This endpoint must be PUBLIC</strong> (no JWT) — Razorpay's servers
 * have no JWT token. The request is authenticated via HMAC-SHA256 signature
 * verification instead (see {@link #verifyWebhookSignature}).
 *
 * <h3>Events handled</h3>
 * <ul>
 *   <li>{@code payout.processed}  — bank transfer confirmed, mark payout PAID</li>
 *   <li>{@code payout.failed}     — transfer failed, mark payout FAILED</li>
 *   <li>{@code payout.reversed}   — transfer reversed after being processed</li>
 * </ul>
 *
 * <h3>Setup in Razorpay Dashboard</h3>
 * <ol>
 *   <li>Go to Settings → Webhooks → Add New Webhook</li>
 *   <li>URL: {@code https://your-domain.com/api/payments/webhook/razorpay}</li>
 *   <li>Secret: set a strong secret and paste it into {@code razorpay.webhook-secret} in application.yml</li>
 *   <li>Check events: payout.processed, payout.failed, payout.reversed</li>
 * </ol>
 *
 * <h3>Local testing</h3>
 * Use the Razorpay Dashboard → Webhooks → "Test Webhook" to send a sample event,
 * or use ngrok to expose localhost:8080 temporarily.
 */
@RestController
@RequestMapping("/api/payments/webhook")
public class RazorpayWebhookController {

    private static final Logger log = LoggerFactory.getLogger(RazorpayWebhookController.class);

    private final OutletPayoutRepository payoutRepo;

    @Value("${razorpay.webhook-secret:NOT_SET}")
    private String webhookSecret;

    public RazorpayWebhookController(OutletPayoutRepository payoutRepo) {
        this.payoutRepo = payoutRepo;
    }

    /**
     * POST /api/payments/webhook/razorpay
     *
     * <p>Razorpay sends the raw JSON body and the header
     * {@code X-Razorpay-Signature} which is HMAC-SHA256(rawBody, webhookSecret).
     * We verify the signature before touching any DB rows.
     */
    @PostMapping("/razorpay")
    public Map<String, String> handleWebhook(
            @RequestBody String rawBody,
            @RequestHeader(value = "X-Razorpay-Signature", required = false) String signature,
            HttpServletRequest request) {

        // ── 1. Verify signature ────────────────────────────────────────────
        if (!"NOT_SET".equals(webhookSecret)) {
            if (signature == null || !verifyWebhookSignature(rawBody, signature)) {
                log.warn("Razorpay webhook received with invalid signature — ignoring.");
                throw new ApiException("Invalid webhook signature", 400);
            }
        } else {
            log.warn("razorpay.webhook-secret is NOT_SET — skipping signature check. Set it in application.yml!");
        }

        // ── 2. Parse event ────────────────────────────────────────────────
        JSONObject payload  = new JSONObject(rawBody);
        String     event    = payload.optString("event", "");
        JSONObject payoutObj = payload
                .optJSONObject("payload") != null
                ? payload.getJSONObject("payload").optJSONObject("payout") : null;

        if (payoutObj == null) {
            log.info("Webhook event '{}' has no payout payload — ignoring.", event);
            return Map.of("status", "ignored");
        }

        JSONObject payoutEntity = payoutObj.optJSONObject("entity");
        if (payoutEntity == null) {
            return Map.of("status", "ignored");
        }

        String rzpPayoutId = payoutEntity.optString("id", null);
        if (rzpPayoutId == null) {
            return Map.of("status", "ignored");
        }

        // ── 3. Find matching OutletPayout row ─────────────────────────────
        OutletPayout payout = payoutRepo.findByRazorpayPayoutId(rzpPayoutId).orElse(null);
        if (payout == null) {
            log.info("Webhook: no OutletPayout found for rzpPayoutId={} — may be a test event.", rzpPayoutId);
            return Map.of("status", "not_found");
        }

        // ── 4. Update status ───────────────────────────────────────────────
        switch (event) {
            case "payout.processed" -> {
                payout.setStatus("PAID");
                log.info("Payout {} marked PAID via webhook.", rzpPayoutId);
            }
            case "payout.failed" -> {
                String failReason = payoutEntity.optString("failure_reason", "unknown");
                payout.setStatus("FAILED");
                payout.setNote("Failure reason: " + failReason);
                log.warn("Payout {} FAILED via webhook. Reason: {}", rzpPayoutId, failReason);
            }
            case "payout.reversed" -> {
                payout.setStatus("REVERSED");
                log.warn("Payout {} REVERSED via webhook.", rzpPayoutId);
            }
            default -> log.info("Unhandled webhook event '{}' — ignoring.", event);
        }

        payoutRepo.save(payout);
        return Map.of("status", "ok");
    }

    // ── Signature verification ────────────────────────────────────────────────

    private boolean verifyWebhookSignature(String rawBody, String receivedSignature) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    webhookSecret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] computed = mac.doFinal(rawBody.getBytes(StandardCharsets.UTF_8));
            String computedHex = HexFormat.of().formatHex(computed);
            return computedHex.equalsIgnoreCase(receivedSignature);
        } catch (Exception e) {
            log.error("Webhook signature verification failed", e);
            return false;
        }
    }
}