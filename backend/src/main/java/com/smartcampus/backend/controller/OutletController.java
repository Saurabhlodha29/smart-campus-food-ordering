package com.smartcampus.backend.controller;

import com.smartcampus.backend.domain.Outlet;
import com.smartcampus.backend.domain.User;
import com.smartcampus.backend.dto.OutletHoursRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.dto.DailyRevenueDto;
import com.smartcampus.backend.repository.MenuItemRepository;
import com.smartcampus.backend.repository.OrderRepository;
import com.smartcampus.backend.repository.OutletRepository;
import com.smartcampus.backend.repository.UserRepository;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import java.time.LocalDateTime;

import java.util.List;
import java.util.Map;

/**
 * Outlet queries and lifecycle actions.
 *
 * Student endpoints:
 * GET /api/outlets/campus/{campusId} — ACTIVE outlets on a campus
 * GET /api/outlets/campus/{campusId}/visible — ACTIVE + CLOSED outlets
 * (greyed-out display)
 *
 * Manager endpoints:
 * GET /api/outlets/mine — the manager's own outlet info
 * POST /api/outlets/{id}/launch — go live (PENDING_LAUNCH → ACTIVE)
 * POST /api/outlets/{id}/toggle — manager open/close toggle (ACTIVE ↔ CLOSED)
 *
 * Admin endpoints:
 * GET /api/outlets/campus/{campusId}/all — all outlets (any status) on their
 * campus
 * POST /api/outlets/{id}/suspend — suspend an outlet (admin-imposed)
 * POST /api/outlets/{id}/reactivate — reactivate a suspended outlet
 * DELETE /api/outlets/{id} — soft-delete an outlet (sets status = DELETED)
 *
 * SuperAdmin endpoints:
 * GET /api/outlets/all — every outlet on the platform
 */
@RestController
@RequestMapping("/api/outlets")
public class OutletController {

    private final OutletRepository outletRepo;
    private final UserRepository userRepo;
    private final MenuItemRepository menuItemRepo;
    private final OrderRepository orderRepo;

    public OutletController(OutletRepository outletRepo,
            UserRepository userRepo,
            MenuItemRepository menuItemRepo,
            OrderRepository orderRepo) {
        this.outletRepo = outletRepo;
        this.userRepo = userRepo;
        this.menuItemRepo = menuItemRepo;
        this.orderRepo = orderRepo;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PUBLIC / AUTHENTICATED — Single outlet by ID (Flutter outlet detail screen)
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * GET /api/outlets/{id}
     * Returns a single outlet. Used by the student outlet detail screen.
     * Any authenticated user can call this — students, managers, admins.
     */
    @GetMapping("/{id}")
    public Outlet getOutletById(@PathVariable Long id) {
        return outletRepo.findById(id)
                .orElseThrow(() -> new ApiException("Outlet not found", 404));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // STUDENT — Active outlets only (ordering screen)
    // ─────────────────────────────────────────────────────────────────────────

    @GetMapping("/campus/{campusId}")
    public List<Outlet> getActiveOutletsForCampus(@PathVariable Long campusId) {
        return outletRepo.findByCampusIdAndStatus(campusId, Outlet.STATUS_ACTIVE);
    }

    /**
     * Returns both ACTIVE and CLOSED outlets so the Flutter UI can show
     * closed outlets greyed out. Students should not order from CLOSED outlets —
     * the order creation endpoint enforces this server-side.
     */
    @GetMapping("/campus/{campusId}/visible")
    public List<Outlet> getVisibleOutletsForCampus(@PathVariable Long campusId) {
        return outletRepo.findByCampusIdAndStatusIn(campusId,
                List.of(Outlet.STATUS_ACTIVE, Outlet.STATUS_CLOSED));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ADMIN — All outlets (any status) for a campus
    // ─────────────────────────────────────────────────────────────────────────

    @GetMapping("/campus/{campusId}/all")
    public List<Outlet> getAllOutletsForCampus(@PathVariable Long campusId) {
        return outletRepo.findByCampusId(campusId);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // SUPERADMIN — All outlets across the whole platform
    // ─────────────────────────────────────────────────────────────────────────

    @GetMapping("/all")
    public List<Outlet> getAllOutlets() {
        return outletRepo.findAll();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // MANAGER — Get their own outlet
    // ─────────────────────────────────────────────────────────────────────────

    @GetMapping("/mine")
    public Outlet getMyOutlet(Authentication auth) {
        User manager = resolveUser(auth);
        return outletRepo.findByManagerId(manager.getId())
                .orElseThrow(() -> new ApiException("No outlet found for your account", 404));
    }

    /**
     * GET /api/outlets/analytics/weekly
     * Returns last 7 days of revenue and order count for the manager's own outlet.
     * Used by Flutter to render a bar chart on the manager dashboard.
     */
    @GetMapping("/analytics/weekly")
    public List<DailyRevenueDto> getWeeklyAnalytics(Authentication auth) {
        User manager = resolveUser(auth);
        Outlet outlet = outletRepo.findByManagerId(manager.getId())
                .orElseThrow(() -> new ApiException("No outlet found for your account", 404));

        LocalDateTime since = LocalDateTime.now().minusDays(7);
        List<Object[]> rows = orderRepo.getDailyRevenueForOutlet(outlet.getId(), since);

        return rows.stream()
                .map(row -> new DailyRevenueDto(
                        row[0].toString(), // date
                        ((Number) row[1]).longValue(), // order_count
                        ((Number) row[2]).doubleValue())) // revenue
                .collect(java.util.stream.Collectors.toList());
    }

    // ─────────────────────────────────────────────────────────────────────────
    // MANAGER — Launch outlet (PENDING_LAUNCH → ACTIVE)
    // ─────────────────────────────────────────────────────────────────────────

    @PostMapping("/{id}/launch")
    public Map<String, Object> launchOutlet(@PathVariable Long id, Authentication auth) {

        User manager = resolveUser(auth);
        Outlet outlet = outletRepo.findById(id)
                .orElseThrow(() -> new ApiException("Outlet not found", 404));

        if (!outlet.getManager().getId().equals(manager.getId())) {
            throw new ApiException("You can only launch your own outlet", 403);
        }
        if (!Outlet.STATUS_PENDING_LAUNCH.equals(outlet.getStatus())) {
            throw new ApiException(
                    "Outlet cannot be launched from status: " + outlet.getStatus(), 400);
        }

        long availableItemCount = menuItemRepo.findByOutletIdAndIsAvailableTrue(id).size();
        if (availableItemCount == 0) {
            throw new ApiException(
                    "Please add at least one menu item before launching your outlet.", 400);
        }

        outlet.launch();
        outletRepo.save(outlet);

        return Map.of(
                "message", "Outlet is now live!",
                "outletId", outlet.getId(),
                "status", outlet.getStatus(),
                "launchedAt", outlet.getLaunchedAt().toString());
    }

    // ─────────────────────────────────────────────────────────────────────────
    // MANAGER — Toggle open / close (ACTIVE ↔ CLOSED)
    // ─────────────────────────────────────────────────────────────────────────

    @PostMapping("/{id}/toggle")
    public Map<String, Object> toggleOutlet(@PathVariable Long id, Authentication auth) {

        User manager = resolveUser(auth);
        Outlet outlet = outletRepo.findById(id)
                .orElseThrow(() -> new ApiException("Outlet not found", 404));

        if (!outlet.getManager().getId().equals(manager.getId())) {
            throw new ApiException("You can only manage your own outlet", 403);
        }

        if (Outlet.STATUS_SUSPENDED.equals(outlet.getStatus())) {
            throw new ApiException(
                    "Your outlet has been suspended by the campus admin. Contact them to reactivate.", 403);
        }
        if (Outlet.STATUS_PENDING_LAUNCH.equals(outlet.getStatus())) {
            throw new ApiException(
                    "Please launch your outlet before toggling open/close.", 400);
        }

        String newStatus = outlet.toggleOpenClose();
        outletRepo.save(outlet);

        String message = Outlet.STATUS_ACTIVE.equals(newStatus)
                ? "Outlet is now open and accepting orders."
                : "Outlet is now closed. Students will see it as unavailable.";

        return Map.of(
                "message", message,
                "outletId", outlet.getId(),
                "status", newStatus);
    }

    /**
     * Manager sets or updates operating hours for their outlet.
     * PATCH /api/outlets/{id}/hours
     * Body: { "openingTime": "08:00", "closingTime": "22:00" }
     * Send nulls to remove the time restriction.
     */
    @PatchMapping("/{id}/hours")
    public Map<String, Object> setOperatingHours(
            @PathVariable Long id,
            @RequestBody OutletHoursRequest request,
            Authentication auth) {

        User manager = resolveUser(auth);
        Outlet outlet = outletRepo.findById(id)
                .orElseThrow(() -> new ApiException("Outlet not found", 404));

        if (!outlet.getManager().getId().equals(manager.getId())) {
            throw new ApiException("You can only update your own outlet", 403);
        }

        outlet.setOpeningTime(request.getOpeningTime());
        outlet.setClosingTime(request.getClosingTime());
        outletRepo.save(outlet);

        return Map.of(
                "message", "Operating hours updated.",
                "outletId", outlet.getId(),
                "openingTime", outlet.getOpeningTime() != null ? outlet.getOpeningTime().toString() : "none",
                "closingTime", outlet.getClosingTime() != null ? outlet.getClosingTime().toString() : "none");
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ADMIN — Suspend / Reactivate (admin-imposed, overrides manager toggle)
    // ─────────────────────────────────────────────────────────────────────────

    @PostMapping("/{id}/suspend")
    public Map<String, String> suspendOutlet(@PathVariable Long id, Authentication auth) {

        User admin = resolveUser(auth);
        Outlet outlet = outletRepo.findById(id)
                .orElseThrow(() -> new ApiException("Outlet not found", 404));

        assertAdminCampusMatch(admin, outlet);

        if (Outlet.STATUS_SUSPENDED.equals(outlet.getStatus())) {
            throw new ApiException("Outlet is already suspended", 400);
        }
        if (Outlet.STATUS_DELETED.equals(outlet.getStatus())) {
            throw new ApiException("Outlet has been deleted and cannot be suspended", 400);
        }

        outlet.setStatus(Outlet.STATUS_SUSPENDED);
        outletRepo.save(outlet);
        return Map.of("message", "Outlet suspended", "outletId", String.valueOf(id));
    }

    @PostMapping("/{id}/reactivate")
    public Map<String, String> reactivateOutlet(@PathVariable Long id, Authentication auth) {

        User admin = resolveUser(auth);
        Outlet outlet = outletRepo.findById(id)
                .orElseThrow(() -> new ApiException("Outlet not found", 404));

        assertAdminCampusMatch(admin, outlet);

        if (!Outlet.STATUS_SUSPENDED.equals(outlet.getStatus())) {
            throw new ApiException("Outlet is not suspended", 400);
        }

        outlet.setStatus(Outlet.STATUS_ACTIVE);
        outletRepo.save(outlet);
        return Map.of("message", "Outlet reactivated", "outletId", String.valueOf(id));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ADMIN — Soft-delete an outlet (sets status = DELETED, not recoverable by
    // admin)
    //
    // This is a soft delete — all historical data (orders, payments, payouts) is
    // preserved. The outlet simply becomes invisible to students and managers.
    // Use suspension for temporary bans; deletion is permanent from the admin UI.
    // ─────────────────────────────────────────────────────────────────────────

    @DeleteMapping("/{id}")
    public Map<String, String> deleteOutlet(@PathVariable Long id, Authentication auth) {

        User admin = resolveUser(auth);
        Outlet outlet = outletRepo.findById(id)
                .orElseThrow(() -> new ApiException("Outlet not found", 404));

        assertAdminCampusMatch(admin, outlet);

        if (Outlet.STATUS_DELETED.equals(outlet.getStatus())) {
            throw new ApiException("Outlet is already deleted", 400);
        }

        outlet.setStatus(Outlet.STATUS_DELETED);
        outletRepo.save(outlet);

        return Map.of(
                "message", "Outlet has been permanently deleted. All historical data is preserved.",
                "outletId", String.valueOf(id));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────────────────

    private User resolveUser(Authentication auth) {
        String email = (String) auth.getPrincipal();
        return userRepo.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", 404));
    }

    private void assertAdminCampusMatch(User admin, Outlet outlet) {
        if (admin.getCampus() == null ||
                !admin.getCampus().getId().equals(outlet.getCampus().getId())) {
            throw new ApiException("You can only manage outlets on your own campus", 403);
        }
    }
}