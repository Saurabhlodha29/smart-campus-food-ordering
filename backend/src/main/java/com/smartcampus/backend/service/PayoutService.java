package com.smartcampus.backend.service;

import com.smartcampus.backend.domain.Outlet;
import com.smartcampus.backend.domain.OutletPayout;
import com.smartcampus.backend.repository.OutletPayoutRepository;
import com.smartcampus.backend.repository.OutletRepository;
import com.smartcampus.backend.repository.OrderRepository;
import com.razorpay.RazorpayException;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Base64;
import java.util.List;

/**
 * Weekly payout scheduler — distributes collected online payments to managers.
 *
 * <h3>When it runs</h3>
 * Every Sunday at 2:00 AM. Covers the 7-day period ending the previous Saturday.
 *
 * <h3>What it processes</h3>
 * All outlets that are ACTIVE or CLOSED (i.e., operational outlets — not SUSPENDED,
 * not DELETED, not PENDING_LAUNCH). An outlet that was temporarily closed one day
 * during the week still deserves its payout for orders placed while it was open.
 *
 * <h3>Online vs Cash split</h3>
 * <ul>
 *   <li><b>ONLINE orders:</b> Money was collected by Razorpay on the platform's behalf.
 *       The platform owes this money (minus commission) to the manager. A real bank
 *       transfer is initiated (or simulated in test mode).</li>
 *   <li><b>CASH/COD orders:</b> Student paid manager directly in cash at pickup.
 *       The platform never held this money, so no transfer is needed. However the
 *       amount and order count are recorded in the payout row for full transparency.</li>
 * </ul>
 *
 * <h3>Skipping outlets</h3>
 * Outlets with ₹0 gross AND ₹0 cash activity are skipped — no point creating an
 * empty payout record. Outlets with only cash activity (grossAmount = 0 but
 * cashGrossAmount > 0) still get a payout record created as SIMULATED with ₹0
 * transfer, so the cash revenue is captured in the admin dashboard.
 *
 * <h3>Test mode (default)</h3>
 * Keep {@code razorpay.payouts-enabled=false}. Records are created as SIMULATED —
 * no real bank transfer happens. Razorpay X requires a live business account.
 *
 * <h3>Why RestTemplate instead of RazorpayClient for payouts?</h3>
 * The {@code razorpay-java} SDK covers the standard Payments API (orders, refunds etc).
 * Contacts, Fund Accounts, and Payouts belong to <b>Razorpay X</b> — a separate product.
 * The SDK does NOT expose {@code razorpayClient.contacts} or {@code razorpayClient.payouts}.
 * We call the Razorpay X REST API directly with Basic Auth via RestTemplate instead.
 */
@Service
public class PayoutService {

    private static final Logger log = LoggerFactory.getLogger(PayoutService.class);

    private static final double COMMISSION_RATE   = 0.05;
    private static final String RAZORPAY_BASE_URL = "https://api.razorpay.com/v1";

    private final OutletRepository       outletRepo;
    private final OrderRepository        orderRepo;
    private final OutletPayoutRepository payoutRepo;
    private final RestTemplate           restTemplate;

    @Value("${razorpay.key-id}")
    private String keyId;

    @Value("${razorpay.key-secret}")
    private String keySecret;

    @Value("${razorpay.payouts-enabled:false}")
    private boolean payoutsEnabled;

    @Value("${razorpay.payout-account-number:NOT_SET}")
    private String payoutAccountNumber;

    public PayoutService(OutletRepository       outletRepo,
                         OrderRepository        orderRepo,
                         OutletPayoutRepository payoutRepo,
                         RestTemplate           restTemplate) {
        this.outletRepo   = outletRepo;
        this.orderRepo    = orderRepo;
        this.payoutRepo   = payoutRepo;
        this.restTemplate = restTemplate;
    }

    // ── Scheduled entry point ─────────────────────────────────────────────────

    @Scheduled(cron = "0 0 2 * * SUN")
    @Transactional
    public void processWeeklyPayouts() {

        LocalDate periodEnd   = LocalDate.now().minusDays(1);   // Yesterday (Saturday)
        LocalDate periodStart = periodEnd.minusDays(6);          // 7 days total (Sun–Sat)

        LocalDateTime periodStartDt = periodStart.atStartOfDay();
        LocalDateTime periodEndDt   = periodEnd.atTime(23, 59, 59);

        log.info("[PayoutService] ═══ Weekly payout run started. Period: {} – {} ═══",
                periodStart, periodEnd);

        // Process ACTIVE and CLOSED outlets — both may have had orders this week.
        // SUSPENDED outlets are excluded: they were penalised and should not receive payouts.
        // DELETED and PENDING_LAUNCH outlets never had PICKED orders so they'd produce ₹0 anyway.
        List<Outlet> eligibleOutlets = outletRepo.findByStatusIn(
                List.of(Outlet.STATUS_ACTIVE, Outlet.STATUS_CLOSED));

        log.info("[PayoutService] Found {} eligible outlet(s) (ACTIVE + CLOSED).",
                eligibleOutlets.size());

        int processed = 0, skipped = 0, failed = 0;

        for (Outlet outlet : eligibleOutlets) {
            try {
                boolean ran = processOutletPayout(
                        outlet, periodStart, periodEnd, periodStartDt, periodEndDt);
                if (ran) processed++; else skipped++;
            } catch (Exception e) {
                failed++;
                log.error("[PayoutService] Payout failed for outlet #{} ({}): {}",
                        outlet.getId(), outlet.getName(), e.getMessage());
            }
        }

        log.info("[PayoutService] ═══ Weekly payout complete. Processed={}, Skipped={}, Failed={} ═══",
                processed, skipped, failed);
    }

    // ── Per-outlet logic ──────────────────────────────────────────────────────

    /**
     * Processes payout for a single outlet.
     * @return true if a payout record was created, false if skipped (duplicate or ₹0 activity).
     */
    private boolean processOutletPayout(Outlet outlet,
                                        LocalDate periodStart, LocalDate periodEnd,
                                        LocalDateTime periodStartDt, LocalDateTime periodEndDt) {

        // Idempotency guard — don't double-pay if the scheduler runs twice
        if (payoutRepo.existsByOutletIdAndPeriodStart(outlet.getId(), periodStart)) {
            log.info("[PayoutService] Duplicate — outlet #{} already processed for period {}.",
                    outlet.getId(), periodStart);
            return false;
        }

        // ── Online revenue (platform-collected) ───────────────────────────────
        double onlineGross = orderRepo.sumOnlinePaidPickedAmountForOutlet(
                outlet.getId(), periodStartDt, periodEndDt);
        long   onlineCount = orderRepo.countOnlinePaidPickedOrdersForOutlet(
                outlet.getId(), periodStartDt, periodEndDt);

        // ── Cash revenue (manager-collected directly, tracking only) ──────────
        double cashGross = orderRepo.sumCashPaidPickedAmountForOutlet(
                outlet.getId(), periodStartDt, periodEndDt);
        long   cashCount = orderRepo.countCashPaidPickedOrdersForOutlet(
                outlet.getId(), periodStartDt, periodEndDt);

        // Skip entirely if there was absolutely no activity this week
        if (onlineGross <= 0 && cashGross <= 0) {
            log.info("[PayoutService] Outlet #{} ({}) — no orders this week. Skipping.",
                    outlet.getId(), outlet.getName());
            return false;
        }

        // ── Build payout record ───────────────────────────────────────────────
        double commissionAmount = Math.round(onlineGross * COMMISSION_RATE * 100.0) / 100.0;
        double netAmount        = Math.round((onlineGross - commissionAmount) * 100.0) / 100.0;

        OutletPayout payout = new OutletPayout(
                outlet, onlineGross, COMMISSION_RATE, commissionAmount,
                netAmount, (int) onlineCount, periodStart, periodEnd);

        // Attach COD tracking fields
        payout.setCashGrossAmount(cashGross);
        payout.setCashOrderCount((int) cashCount);

        log.info("[PayoutService] Outlet #{} ({}) | Online: ₹{} ({} orders) | Cash: ₹{} ({} orders) | Net transfer: ₹{}",
                outlet.getId(), outlet.getName(),
                onlineGross, onlineCount,
                cashGross, cashCount,
                netAmount);

        // ── Test / simulated mode (default) ──────────────────────────────────
        if (!payoutsEnabled) {
            payout.setStatus("SIMULATED");
            payout.setNote(String.format(
                    "Simulated. Online gross=₹%.2f, Commission=₹%.2f, Net=₹%.2f | Cash (not transferred)=₹%.2f",
                    onlineGross, commissionAmount, netAmount, cashGross));
            payoutRepo.save(payout);
            log.info("[PayoutService] [SIMULATED] Outlet #{} payout record created.", outlet.getId());
            return true;
        }

        // ── Live Razorpay X transfer ──────────────────────────────────────────
        // If there's nothing to transfer online (only cash orders this week), still
        // create the record but mark it SIMULATED — no actual transfer needed.
        if (onlineGross <= 0) {
            payout.setStatus("SIMULATED");
            payout.setNote(String.format(
                    "No online revenue this week. Cash revenue of ₹%.2f collected directly by manager.",
                    cashGross));
            payoutRepo.save(payout);
            log.info("[PayoutService] Outlet #{} — only cash orders this week; no transfer needed.", outlet.getId());
            return true;
        }

        if (!outlet.hasBankDetails()) {
            payout.setStatus("FAILED");
            payout.setNote("No bank details on file for this outlet. Manager must add bank details.");
            payoutRepo.save(payout);
            log.warn("[PayoutService] Outlet #{} has no bank details — payout FAILED.", outlet.getId());
            return true;
        }

        try {
            String fundAccountId = getOrCreateFundAccount(outlet);
            String rzpPayoutId   = initiateRazorpayPayout(
                    fundAccountId, netAmount, outlet.getId(), periodStart, periodEnd);

            payout.setRazorpayPayoutId(rzpPayoutId);
            payout.setStatus("PROCESSING");
            payout.setNote("Razorpay X payout initiated. Awaiting webhook confirmation.");
            payoutRepo.save(payout);

        } catch (Exception e) {
            payout.setStatus("FAILED");
            payout.setNote("Razorpay X error: " + e.getMessage());
            payoutRepo.save(payout);
            log.error("[PayoutService] Razorpay X error for outlet #{}: {}",
                    outlet.getId(), e.getMessage());
        }

        return true;
    }

    // ── Razorpay X — direct REST calls ────────────────────────────────────────

    private String getOrCreateFundAccount(Outlet outlet) {

        if (outlet.getRazorpayFundAccountId() != null
                && !outlet.getRazorpayFundAccountId().isBlank()) {
            return outlet.getRazorpayFundAccountId();
        }

        HttpHeaders headers = buildAuthHeaders();

        // 1. Create Contact
        JSONObject contactReq = new JSONObject();
        contactReq.put("name",         outlet.getName());
        contactReq.put("type",         "vendor");
        contactReq.put("reference_id", "outlet_" + outlet.getId());

        ResponseEntity<String> contactResp = restTemplate.exchange(
                RAZORPAY_BASE_URL + "/contacts",
                HttpMethod.POST,
                new HttpEntity<>(contactReq.toString(), headers),
                String.class
        );
        String contactId = new JSONObject(contactResp.getBody()).getString("id");
        log.info("[PayoutService] Created Contact {} for outlet #{}", contactId, outlet.getId());

        // 2. Create Fund Account
        JSONObject bankAccount = new JSONObject();
        bankAccount.put("name",           outlet.getBankAccountHolderName());
        bankAccount.put("ifsc",           outlet.getBankIfscCode());
        bankAccount.put("account_number", outlet.getBankAccountNumber());

        JSONObject fundAccReq = new JSONObject();
        fundAccReq.put("contact_id",   contactId);
        fundAccReq.put("account_type", "bank_account");
        fundAccReq.put("bank_account", bankAccount);

        ResponseEntity<String> fundAccResp = restTemplate.exchange(
                RAZORPAY_BASE_URL + "/fund_accounts",
                HttpMethod.POST,
                new HttpEntity<>(fundAccReq.toString(), headers),
                String.class
        );
        String fundAccountId = new JSONObject(fundAccResp.getBody()).getString("id");
        log.info("[PayoutService] Created FundAccount {} for outlet #{}", fundAccountId, outlet.getId());

        // 3. Persist both IDs so we never recreate them
        outlet.setRazorpayContactId(contactId);
        outlet.setRazorpayFundAccountId(fundAccountId);
        outletRepo.save(outlet);

        return fundAccountId;
    }

    private String initiateRazorpayPayout(String fundAccountId, double netAmount,
                                           Long outletId, LocalDate periodStart,
                                           LocalDate periodEnd) {

        int amountInPaise = (int) Math.round(netAmount * 100);

        JSONObject payoutReq = new JSONObject();
        payoutReq.put("account_number",       payoutAccountNumber);
        payoutReq.put("fund_account_id",      fundAccountId);
        payoutReq.put("amount",               amountInPaise);
        payoutReq.put("currency",             "INR");
        payoutReq.put("mode",                 "NEFT");
        payoutReq.put("purpose",              "vendor_advance");
        payoutReq.put("narration",            "Campus Food Settlement " + periodStart + " to " + periodEnd);
        payoutReq.put("reference_id",         "payout_outlet_" + outletId + "_" + periodStart);
        payoutReq.put("queue_if_low_balance", true);

        ResponseEntity<String> resp = restTemplate.exchange(
                RAZORPAY_BASE_URL + "/payouts",
                HttpMethod.POST,
                new HttpEntity<>(payoutReq.toString(), buildAuthHeaders()),
                String.class
        );

        String rzpPayoutId = new JSONObject(resp.getBody()).getString("id");
        log.info("[PayoutService] Razorpay X payout {} created for outlet #{}", rzpPayoutId, outletId);
        return rzpPayoutId;
    }

    private HttpHeaders buildAuthHeaders() {
        String credentials = keyId + ":" + keySecret;
        String encoded     = Base64.getEncoder()
                .encodeToString(credentials.getBytes(StandardCharsets.UTF_8));
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Basic " + encoded);
        headers.setContentType(MediaType.APPLICATION_JSON);
        return headers;
    }

    // ── Manual retry (SUPERADMIN) ─────────────────────────────────────────────

    @Transactional
    public OutletPayout retryPayout(Long payoutId) throws RazorpayException {

        OutletPayout payout = payoutRepo.findById(payoutId)
                .orElseThrow(() -> new RuntimeException("Payout not found: " + payoutId));

        if (!"FAILED".equals(payout.getStatus())) {
            throw new IllegalStateException("Can only retry FAILED payouts.");
        }

        Outlet outlet = payout.getOutlet();

        if (!payoutsEnabled) {
            payout.setStatus("SIMULATED");
            payout.setNote("Manual retry — simulated (Razorpay X not enabled).");
            return payoutRepo.save(payout);
        }

        String fundAccountId = getOrCreateFundAccount(outlet);
        String rzpPayoutId   = initiateRazorpayPayout(
                fundAccountId, payout.getNetAmount(),
                outlet.getId(), payout.getPeriodStart(), payout.getPeriodEnd());

        payout.setRazorpayPayoutId(rzpPayoutId);
        payout.setStatus("PROCESSING");
        payout.setNote("Manually retried. Awaiting webhook confirmation.");
        return payoutRepo.save(payout);
    }
}