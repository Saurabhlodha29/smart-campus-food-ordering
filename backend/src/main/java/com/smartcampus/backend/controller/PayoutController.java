package com.smartcampus.backend.controller;

import com.smartcampus.backend.dto.OutletBankDetailsRequest;
import com.smartcampus.backend.domain.Outlet;
import com.smartcampus.backend.domain.OutletPayout;
import com.smartcampus.backend.domain.User;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.OutletPayoutRepository;
import com.smartcampus.backend.repository.OutletRepository;
import com.smartcampus.backend.repository.UserRepository;
import com.smartcampus.backend.service.PayoutService;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Payout history and retry endpoints.
 *
 * <pre>
 * GET  /api/payouts/my-outlet              MANAGER    — payout history for their outlet
 * GET  /api/payouts/campus                 ADMIN      — payout history for all outlets on their campus
 * GET  /api/payouts/outlet/{outletId}      SUPERADMIN — payout history for any outlet
 * GET  /api/payouts/all                    SUPERADMIN — all payouts across platform
 * GET  /api/payouts/failed                 SUPERADMIN — all FAILED payouts
 * POST /api/payouts/{payoutId}/retry       SUPERADMIN — retry a FAILED payout
 * GET  /api/payouts/summary/{outletId}     SUPERADMIN — total earned by an outlet
 * </pre>
 *
 * Security is declared in SecurityConfig. Role checks here are a secondary safety net.
 */
@RestController
@RequestMapping("/api/payouts")
public class PayoutController {

    private final OutletPayoutRepository payoutRepo;
    private final OutletRepository       outletRepo;
    private final UserRepository         userRepo;
    private final PayoutService          payoutService;

    public PayoutController(OutletPayoutRepository payoutRepo,
                            OutletRepository       outletRepo,
                            UserRepository         userRepo,
                            PayoutService          payoutService) {
        this.payoutRepo    = payoutRepo;
        this.outletRepo    = outletRepo;
        this.userRepo      = userRepo;
        this.payoutService = payoutService;
    }

    // ── MANAGER ───────────────────────────────────────────────────────────────

    /**
     * Returns the full payout history for the authenticated manager's outlet,
     * newest first.
     *
     * <pre>GET /api/payouts/my-outlet</pre>
     */
    @GetMapping("/my-outlet")
    public List<OutletPayout> getMyOutletPayouts(Authentication auth) {

        User manager = resolveUser(auth);
        Outlet outlet = outletRepo.findByManagerId(manager.getId())
                .orElseThrow(() -> new ApiException("No outlet found for this manager.", 404));

        return payoutRepo.findByOutletIdOrderByCreatedAtDesc(outlet.getId());
    }

    // ── ADMIN ─────────────────────────────────────────────────────────────────

    /**
     * All payout records for every outlet on the authenticated admin's campus,
     * newest first. Gives campus admins full visibility into weekly settlement history
     * including both the online transfer amounts and the COD (cash) tracking figures.
     *
     * <pre>GET /api/payouts/campus</pre>
     */
    @GetMapping("/campus")
    public List<OutletPayout> getCampusPayouts(Authentication auth) {

        User admin = resolveUser(auth);

        if (admin.getCampus() == null) {
            throw new ApiException("Your account is not assigned to any campus.", 400);
        }

        return payoutRepo.findByCampusIdOrderByCreatedAtDesc(admin.getCampus().getId());
    }

    // ── SUPERADMIN ────────────────────────────────────────────────────────────

    /**
     * All payouts for a specific outlet, newest first.
     *
     * <pre>GET /api/payouts/outlet/{outletId}</pre>
     */
    @GetMapping("/outlet/{outletId}")
    public List<OutletPayout> getPayoutsForOutlet(@PathVariable Long outletId) {
        outletRepo.findById(outletId)
                .orElseThrow(() -> new ApiException("Outlet not found: " + outletId, 404));
        return payoutRepo.findByOutletIdOrderByCreatedAtDesc(outletId);
    }

    /**
     * All payouts across the entire platform, newest first.
     *
     * <pre>GET /api/payouts/all</pre>
     */
    @GetMapping("/all")
    public List<OutletPayout> getAllPayouts() {
        return payoutRepo.findAllByOrderByCreatedAtDesc();
    }

    /**
     * All FAILED payouts — for monitoring / ops dashboard.
     *
     * <pre>GET /api/payouts/failed</pre>
     */
    @GetMapping("/failed")
    public List<OutletPayout> getFailedPayouts() {
        return payoutRepo.findFailedPayouts();
    }

    /**
     * Retry a FAILED payout. Delegates to PayoutService which re-attempts
     * the Razorpay X transfer (or re-creates a SIMULATED record in test mode).
     *
     * <pre>POST /api/payouts/{payoutId}/retry</pre>
     */
    @PostMapping("/{payoutId}/retry")
    public Map<String, Object> retryPayout(@PathVariable Long payoutId) {

        OutletPayout payout = payoutRepo.findById(payoutId)
                .orElseThrow(() -> new ApiException("Payout not found: " + payoutId, 404));

        if (!"FAILED".equals(payout.getStatus())) {
            throw new ApiException(
                "Only FAILED payouts can be retried. Current status: " + payout.getStatus(), 400);
        }

        OutletPayout updated;
        try {
            updated = payoutService.retryPayout(payoutId);
        } catch (Exception e) {
            throw new ApiException("Retry failed: " + e.getMessage(), 500);
        }

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("payoutId",   payoutId);
        response.put("newStatus",  updated.getStatus());
        response.put("message",    "Retry initiated.");
        return response;
    }

    /**
     * Total net amount successfully paid to an outlet (SIMULATED + PAID statuses).
     * Useful for the superadmin accounting screen.
     *
     * <pre>GET /api/payouts/summary/{outletId}</pre>
     */
    @GetMapping("/summary/{outletId}")
    public Map<String, Object> getPayoutSummary(@PathVariable Long outletId) {

        Outlet outlet = outletRepo.findById(outletId)
                .orElseThrow(() -> new ApiException("Outlet not found: " + outletId, 404));

        double totalPaid = payoutRepo.sumPaidNetAmount(outletId);
        long   count     = payoutRepo.findByOutletIdOrderByCreatedAtDesc(outletId).size();

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("outletId",        outletId);
        response.put("outletName",      outlet.getName());
        response.put("totalPayouts",    count);
        response.put("totalNetPaid",    totalPaid);
        return response;
    }

    // ── Bank details (MANAGER, mapped here for convenience) ───────────────────

    @PatchMapping("/mine/bank-details")
    public Map<String, Object> saveBankDetails(
            @RequestBody OutletBankDetailsRequest req,
            Authentication auth) {

        User manager = resolveUser(auth);
        Outlet outlet = outletRepo.findByManagerId(manager.getId())
                .orElseThrow(() -> new ApiException("No outlet found for this manager", 404));

        outlet.setBankAccountNumber(req.getBankAccountNumber());
        outlet.setBankIfscCode(req.getBankIfscCode());
        outlet.setBankAccountHolderName(req.getBankAccountHolderName());

        outletRepo.save(outlet);

        return Map.of(
            "message",       "Bank details saved.",
            "outletId",      outlet.getId(),
            "accountHolder", req.getBankAccountHolderName()
        );
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private User resolveUser(Authentication auth) {
        String email = auth.getName();
        return userRepo.findByEmail(email)
                .orElseThrow(() -> new ApiException("Authenticated user not found.", 404));
    }
}