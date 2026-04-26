package com.smartcampus.backend.controller;

import com.smartcampus.backend.domain.Campus;
import com.smartcampus.backend.domain.Notification;
import com.smartcampus.backend.domain.Outlet;
import com.smartcampus.backend.domain.OutletApplication;
import com.smartcampus.backend.domain.Role;
import com.smartcampus.backend.domain.User;
import com.smartcampus.backend.domain.VerificationReport;
import com.smartcampus.backend.dto.OutletApplicationRequest;
import com.smartcampus.backend.dto.OutletApplicationReviewRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.CampusRepository;
import com.smartcampus.backend.repository.NotificationRepository;
import com.smartcampus.backend.repository.OutletApplicationRepository;
import com.smartcampus.backend.repository.OutletRepository;
import com.smartcampus.backend.repository.RoleRepository;
import com.smartcampus.backend.repository.UserRepository;
import com.smartcampus.backend.repository.VerificationReportRepository;
import com.smartcampus.backend.service.DocumentVerificationService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Outlet application lifecycle — manager applies, campus Admin reviews.
 *
 * Public endpoints:
 * POST /api/outlet-applications — submit application (triggers async doc
 * verification)
 *
 * Admin-only endpoints:
 * GET /api/outlet-applications/pending — pending for this admin's campus
 * GET /api/outlet-applications/all — all (any status) for this admin's campus
 * GET /api/outlet-applications/{id}/verification-report — view verification
 * report for an application
 * PATCH /api/outlet-applications/{id}/approve
 * PATCH /api/outlet-applications/{id}/reject
 *
 * SuperAdmin-only:
 * GET /api/outlet-applications/platform-pending — all pending platform-wide
 */
@RestController
@RequestMapping("/api/outlet-applications")
public class OutletApplicationController {

    private final OutletApplicationRepository outletAppRepo;
    private final CampusRepository campusRepo;
    private final OutletRepository outletRepo;
    private final UserRepository userRepo;
    private final RoleRepository roleRepo;
    private final NotificationRepository notifRepo;
    private final PasswordEncoder passwordEncoder;
    private final DocumentVerificationService verificationService;
    private final VerificationReportRepository verificationReportRepo;

    public OutletApplicationController(OutletApplicationRepository outletAppRepo,
            CampusRepository campusRepo,
            OutletRepository outletRepo,
            UserRepository userRepo,
            RoleRepository roleRepo,
            NotificationRepository notifRepo,
            PasswordEncoder passwordEncoder,
            DocumentVerificationService verificationService,
            VerificationReportRepository verificationReportRepo) {
        this.outletAppRepo = outletAppRepo;
        this.campusRepo = campusRepo;
        this.outletRepo = outletRepo;
        this.userRepo = userRepo;
        this.roleRepo = roleRepo;
        this.notifRepo = notifRepo;
        this.passwordEncoder = passwordEncoder;
        this.verificationService = verificationService;
        this.verificationReportRepo = verificationReportRepo;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PUBLIC — Submit application (manager doesn't have an account yet)
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Submits an outlet application and immediately triggers async document
     * verification. The caller gets a response right away; verification
     * runs in the background and completes within a few seconds.
     */
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public OutletApplication submitApplication(@Valid @RequestBody OutletApplicationRequest req) {

        Campus campus = campusRepo.findById(req.getCampusId())
                .orElseThrow(() -> new ApiException("Campus not found", 404));

        String managerEmail = req.getManagerEmail().toLowerCase().trim();

        // Manager email must belong to the campus email domain
        String emailDomain = managerEmail.substring(managerEmail.indexOf('@') + 1);
        if (!emailDomain.equalsIgnoreCase(campus.getEmailDomain())) {
            throw new ApiException(
                    "Your email domain (" + emailDomain + ") does not match the campus domain ("
                            + campus.getEmailDomain() + ")",
                    400);
        }

        // Enforce max 3 attempts per manager email
        long previousAttempts = outletAppRepo.countByManagerEmail(managerEmail);
        if (previousAttempts >= OutletApplication.MAX_ATTEMPTS) {
            throw new ApiException("You have reached the maximum number of applications (3) for this email.", 403);
        }

        // Must not have a currently PENDING application
        boolean hasPending = outletAppRepo.findByManagerEmail(managerEmail).stream()
                .anyMatch(a -> OutletApplication.STATUS_PENDING.equals(a.getStatus()));
        if (hasPending) {
            throw new ApiException("You already have a pending application. Please wait for a review.", 409);
        }

        // Build the application with document fields
        OutletApplication app = new OutletApplication(
                req.getManagerName(),
                managerEmail,
                req.getOutletName(),
                req.getOutletDescription(),
                req.getAvgPrepTime(),
                req.getLicenseDocUrl(),
                req.getOutletPhotoUrl(),
                campus,
                (int) previousAttempts + 1,
                req.getFssaiLicenseNumber(),
                req.getGstin(),
                req.getPanNumber(),
                req.getBankAccountNumber(),
                req.getBankIfscCode());

        OutletApplication saved = outletAppRepo.save(app);

        // Kick off async verification — returns immediately, runs in background
        verificationService.verifyApplicationAsync(saved);

        return saved;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ADMIN — Verification report
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Returns the automated verification report for a specific application.
     * If verification is still running, the report will show status=PENDING.
     * The admin should call this before reviewing the application.
     */
    @GetMapping("/{id}/verification-report")
    public VerificationReport getVerificationReport(@PathVariable Long id,
            Authentication auth) {
        User admin = resolveAdmin(auth);

        OutletApplication app = outletAppRepo.findById(id)
                .orElseThrow(() -> new ApiException("Application not found", 404));

        if (!app.getCampus().getId().equals(admin.getCampus().getId())) {
            throw new ApiException("You can only view reports for your own campus.", 403);
        }

        return verificationReportRepo.findByOutletApplicationId(id)
                .orElseThrow(() -> new ApiException(
                        "Verification report not yet available — please retry in a few seconds.", 404));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ADMIN — Dashboard for their own campus
    // ─────────────────────────────────────────────────────────────────────────

    @GetMapping("/pending")
    public List<OutletApplication> getPendingForMyCampus(Authentication auth) {
        User admin = resolveAdmin(auth);
        return outletAppRepo.findByCampusIdAndStatusOrderByCreatedAtDesc(
                admin.getCampus().getId(), OutletApplication.STATUS_PENDING);
    }

    @GetMapping("/all")
    public List<OutletApplication> getAllForMyCampus(Authentication auth) {
        User admin = resolveAdmin(auth);
        return outletAppRepo.findByCampusIdOrderByCreatedAtDesc(admin.getCampus().getId());
    }

    // ─────────────────────────────────────────────────────────────────────────
    // SUPERADMIN — Platform-wide view
    // ─────────────────────────────────────────────────────────────────────────

    @GetMapping("/platform-pending")
    public List<OutletApplication> getAllPendingPlatformWide() {
        return outletAppRepo.findByStatusOrderByCreatedAtDesc(OutletApplication.STATUS_PENDING);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ADMIN — Approve
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Approving an outlet application:
     * 1. Creates the Outlet in PENDING_LAUNCH state.
     * 2. Creates the Manager user account.
     * 3. Links the created outlet to the application.
     * 4. Sends in-app notification to the manager.
     *
     * The manager then logs in, adds menu items, and clicks "Launch Outlet"
     * to go live (handled by OutletController#launchOutlet).
     */
    @PatchMapping("/{id}/approve")
    public Map<String, Object> approveApplication(@PathVariable Long id,
            @Valid @RequestBody OutletApplicationReviewRequest req,
            Authentication auth) {
        User admin = resolveAdmin(auth);

        OutletApplication app = outletAppRepo.findById(id)
                .orElseThrow(() -> new ApiException("Application not found", 404));

        if (!app.getCampus().getId().equals(admin.getCampus().getId())) {
            throw new ApiException("You can only review applications for your own campus.", 403);
        }
        if (!OutletApplication.STATUS_PENDING.equals(app.getStatus())) {
            throw new ApiException("Application is not in PENDING state", 400);
        }
        if (req.getTemporaryPassword() == null || req.getTemporaryPassword().isBlank()) {
            throw new ApiException("temporaryPassword is required when approving", 400);
        }

        // Warn in the response if verification shows failure (but don't block)
        boolean verificationFailed = verificationReportRepo
                .findByOutletApplicationId(id)
                .map(r -> VerificationReport.STATUS_FAILED.equals(r.getOverallStatus()))
                .orElse(false);

        // Step 1: Create Manager user account
        Role managerRole = roleRepo.findByName("MANAGER")
                .orElseThrow(() -> new ApiException("MANAGER role not seeded — run DataInitializer", 500));

        User manager = new User(
                app.getManagerName(),
                app.getManagerEmail(),
                passwordEncoder.encode(req.getTemporaryPassword()),
                managerRole,
                app.getCampus());
        userRepo.save(manager);

        // Step 2: Create Outlet
        Outlet finalOutlet = new Outlet(
                app.getOutletName(),
                app.getCampus(),
                manager,
                Outlet.STATUS_PENDING_LAUNCH,
                app.getAvgPrepTime(),
                app.getOutletPhotoUrl());
        // Pre-fill bank details from the application if provided
        if (app.getBankAccountNumber() != null)
            finalOutlet.setBankAccountNumber(app.getBankAccountNumber());
        if (app.getBankIfscCode() != null)
            finalOutlet.setBankIfscCode(app.getBankIfscCode());
        if (app.getManagerName() != null)
            finalOutlet.setBankAccountHolderName(app.getManagerName());
        outletRepo.save(finalOutlet);

        // Step 3: Update application
        app.approve(finalOutlet);
        outletAppRepo.save(app);

        // In-app notification to manager
        String msg = req.getMessage() != null && !req.getMessage().isBlank()
                ? req.getMessage()
                : "Your outlet \"" + finalOutlet.getName() + "\" has been approved! "
                        + "Log in with the credentials shared with you, add your menu items, "
                        + "and click 'Launch Outlet' to go live.";

        notifRepo.save(new Notification(
                manager,
                "Outlet Application Approved",
                msg,
                Notification.TYPE_OUTLET_APP_APPROVED));

        Map<String, Object> response = new java.util.LinkedHashMap<>();
        response.put("message", "Application approved. Outlet and manager account created.");
        response.put("outletId", finalOutlet.getId());
        response.put("managerUserId", manager.getId());
        response.put("outletStatus", finalOutlet.getStatus());
        if (verificationFailed) {
            response.put("verificationWarning",
                    "⚠️ This application had a FAILED verification score. You have approved it manually.");
        }
        return response;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ADMIN — Reject
    // ─────────────────────────────────────────────────────────────────────────

    @PatchMapping("/{id}/reject")
    public Map<String, String> rejectApplication(@PathVariable Long id,
            @RequestBody OutletApplicationReviewRequest req,
            Authentication auth) {
        User admin = resolveAdmin(auth);

        OutletApplication app = outletAppRepo.findById(id)
                .orElseThrow(() -> new ApiException("Application not found", 404));

        if (!app.getCampus().getId().equals(admin.getCampus().getId())) {
            throw new ApiException("You can only review applications for your own campus.", 403);
        }
        if (!OutletApplication.STATUS_PENDING.equals(app.getStatus())) {
            throw new ApiException("Application is not in PENDING state", 400);
        }

        String reason = (req.getMessage() != null && !req.getMessage().isBlank())
                ? req.getMessage()
                : "Your application did not meet the requirements at this time.";

        app.reject(reason);
        outletAppRepo.save(app);

        long totalAttempts = outletAppRepo.countByManagerEmail(app.getManagerEmail());
        int remaining = OutletApplication.MAX_ATTEMPTS - (int) totalAttempts;

        return Map.of(
                "message", "Application rejected.",
                "reason", reason,
                "remainingAttempts", String.valueOf(Math.max(0, remaining)));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Helper
    // ─────────────────────────────────────────────────────────────────────────

    private User resolveAdmin(Authentication auth) {
        String email = (String) auth.getPrincipal();
        User admin = userRepo.findByEmail(email)
                .orElseThrow(() -> new ApiException("Authenticated user not found", 404));
        if (admin.getCampus() == null) {
            throw new ApiException("Admin is not assigned to any campus", 400);
        }
        return admin;
    }
}