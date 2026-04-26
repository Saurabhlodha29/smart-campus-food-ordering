package com.smartcampus.backend.controller;

import com.smartcampus.backend.domain.AdminApplication;
import com.smartcampus.backend.domain.Campus;
import com.smartcampus.backend.domain.Notification;
import com.smartcampus.backend.domain.Role;
import com.smartcampus.backend.domain.User;
import com.smartcampus.backend.dto.AdminApplicationRequest;
import com.smartcampus.backend.dto.AdminApplicationReviewRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.AdminApplicationRepository;
import com.smartcampus.backend.repository.CampusRepository;
import com.smartcampus.backend.repository.NotificationRepository;
import com.smartcampus.backend.repository.RoleRepository;
import com.smartcampus.backend.repository.UserRepository;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Handles the Campus Admin application lifecycle.
 *
 * Public endpoints (no token required):
 *   POST   /api/admin-applications          — submit application
 *
 * SuperAdmin-only endpoints:
 *   GET    /api/admin-applications           — list all pending
 *   GET    /api/admin-applications/all       — list all (any status)
 *   PATCH  /api/admin-applications/{id}/approve
 *   PATCH  /api/admin-applications/{id}/reject
 */
@RestController
@RequestMapping("/api/admin-applications")
public class AdminApplicationController {

    private final AdminApplicationRepository adminAppRepo;
    private final CampusRepository           campusRepo;
    private final UserRepository             userRepo;
    private final RoleRepository             roleRepo;
    private final NotificationRepository     notifRepo;
    private final PasswordEncoder            passwordEncoder;

    public AdminApplicationController(AdminApplicationRepository adminAppRepo,
                                       CampusRepository campusRepo,
                                       UserRepository userRepo,
                                       RoleRepository roleRepo,
                                       NotificationRepository notifRepo,
                                       PasswordEncoder passwordEncoder) {
        this.adminAppRepo    = adminAppRepo;
        this.campusRepo      = campusRepo;
        this.userRepo        = userRepo;
        this.roleRepo        = roleRepo;
        this.notifRepo       = notifRepo;
        this.passwordEncoder = passwordEncoder;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PUBLIC — Submit a new admin application
    // ─────────────────────────────────────────────────────────────────────────

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public AdminApplication submitApplication(@Valid @RequestBody AdminApplicationRequest req) {

        String email  = req.getApplicantEmail().toLowerCase().trim();
        String domain = req.getCampusEmailDomain().toLowerCase().trim();

        // 1. Email domain must match the claimed campus domain
        String emailDomain = email.substring(email.indexOf('@') + 1);
        if (!emailDomain.equalsIgnoreCase(domain)) {
            throw new ApiException(
                "Your email domain (" + emailDomain + ") does not match the claimed campus domain (" + domain + ")", 400);
        }

        // 2. Check this email domain doesn't already have an APPROVED campus
        if (campusRepo.existsByEmailDomain(domain)) {
            throw new ApiException("A campus with this email domain already exists on the platform.", 409);
        }
        if (adminAppRepo.existsByCampusEmailDomainAndStatus(domain, AdminApplication.STATUS_APPROVED)) {
            throw new ApiException("An approved application for this campus domain already exists.", 409);
        }

        // 3. Enforce max 3 attempts per email
        long previousAttempts = adminAppRepo.countByApplicantEmail(email);
        if (previousAttempts >= AdminApplication.MAX_ATTEMPTS) {
            throw new ApiException("You have reached the maximum number of applications (3) for this email.", 403);
        }

        // 4. Must not already have a PENDING application
        boolean hasPending = adminAppRepo.findByApplicantEmail(email).stream()
                .anyMatch(a -> AdminApplication.STATUS_PENDING.equals(a.getStatus()));
        if (hasPending) {
            throw new ApiException("You already have a pending application. Please wait for a review.", 409);
        }

        AdminApplication app = new AdminApplication(
                req.getFullName(),
                email,
                req.getDesignation(),
                req.getIdCardPhotoUrl(),
                req.getCampusName(),
                req.getCampusLocation(),
                domain,
                (int) previousAttempts + 1
        );

        return adminAppRepo.save(app);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // SUPERADMIN — Dashboard
    // ─────────────────────────────────────────────────────────────────────────

    /** All PENDING applications — main SuperAdmin dashboard view. */
    @GetMapping
    public List<AdminApplication> getPendingApplications() {
        return adminAppRepo.findByStatusOrderByCreatedAtDesc(AdminApplication.STATUS_PENDING);
    }

    /** All applications regardless of status. */
    @GetMapping("/all")
    public List<AdminApplication> getAllApplications() {
        return adminAppRepo.findAll();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // SUPERADMIN — Approve
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Approving an application:
     *  1. Creates the Campus record.
     *  2. Creates the Admin user account with the temporary password.
     *  3. Marks the application APPROVED and links the created campus.
     *  4. Sends an in-app notification to the new admin (they'll also get
     *     the credentials via email — done outside the platform per your design).
     */
    @PatchMapping("/{id}/approve")
    public Map<String, Object> approveApplication(@PathVariable Long id,
                                                   @Valid @RequestBody AdminApplicationReviewRequest req) {

        AdminApplication app = adminAppRepo.findById(id)
                .orElseThrow(() -> new ApiException("Application not found", 404));

        if (!AdminApplication.STATUS_PENDING.equals(app.getStatus())) {
            throw new ApiException("Application is not in PENDING state", 400);
        }
        if (req.getTemporaryPassword() == null || req.getTemporaryPassword().isBlank()) {
            throw new ApiException("temporaryPassword is required when approving", 400);
        }

        // Create Campus
        Campus campus = new Campus(
                app.getCampusName(),
                app.getCampusLocation(),
                app.getCampusEmailDomain(),
                "ACTIVE"
        );
        campusRepo.save(campus);

        // Create Admin user
        Role adminRole = roleRepo.findByName("ADMIN")
                .orElseThrow(() -> new ApiException("ADMIN role not seeded — run DataInitializer", 500));

        User adminUser = new User(
                app.getFullName(),
                app.getApplicantEmail(),
                passwordEncoder.encode(req.getTemporaryPassword()),
                adminRole,
                campus
        );
        userRepo.save(adminUser);

        // Update application
        app.approve(campus);
        adminAppRepo.save(app);

        // In-app notification
        String welcomeMsg = req.getMessage() != null && !req.getMessage().isBlank()
                ? req.getMessage()
                : "Congratulations! Your application to manage campus \"" + campus.getName()
                  + "\" has been approved. Please log in with the credentials shared with you via email.";

        notifRepo.save(new Notification(
                adminUser,
                "Admin Application Approved",
                welcomeMsg,
                Notification.TYPE_ADMIN_APP_APPROVED
        ));

        return Map.of(
                "message", "Application approved. Campus and admin account created.",
                "campusId", campus.getId(),
                "adminUserId", adminUser.getId()
        );
    }

    // ─────────────────────────────────────────────────────────────────────────
    // SUPERADMIN — Reject
    // ─────────────────────────────────────────────────────────────────────────

    @PatchMapping("/{id}/reject")
    public Map<String, String> rejectApplication(@PathVariable Long id,
                                                  @RequestBody AdminApplicationReviewRequest req) {

        AdminApplication app = adminAppRepo.findById(id)
                .orElseThrow(() -> new ApiException("Application not found", 404));

        if (!AdminApplication.STATUS_PENDING.equals(app.getStatus())) {
            throw new ApiException("Application is not in PENDING state", 400);
        }

        String reason = (req.getMessage() != null && !req.getMessage().isBlank())
                ? req.getMessage()
                : "Your application did not meet the requirements at this time.";

        app.reject(reason);
        adminAppRepo.save(app);

        // Remaining attempts info
        long totalAttempts = adminAppRepo.countByApplicantEmail(app.getApplicantEmail());
        int remaining = AdminApplication.MAX_ATTEMPTS - (int) totalAttempts;

        return Map.of(
                "message", "Application rejected.",
                "reason", reason,
                "remainingAttempts", String.valueOf(Math.max(0, remaining))
        );
    }
}