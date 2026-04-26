package com.smartcampus.backend.controller;

import java.util.List;
import java.util.Map;

import com.smartcampus.backend.domain.*;
import com.smartcampus.backend.dto.UserRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.*;

import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

/**
 * User management endpoints.
 *
 * Self-service (all roles):
 * GET /api/users/me — own profile (name, campus, role, penalty info)
 * PATCH /api/users/me/password — change password (requires currentPassword)
 * PATCH /api/users/me/profile — update name / phone
 *
 * Admin / SuperAdmin:
 * GET /api/users — all users (SuperAdmin only)
 * POST /api/users — create user manually (SuperAdmin)
 * GET /api/users/campus/{id} — users on a campus (Admin / SuperAdmin)
 */
@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserRepository userRepository;
    private final RoleRepository roleRepository;
    private final CampusRepository campusRepository;
    private final PasswordEncoder passwordEncoder;

    public UserController(UserRepository userRepository,
            RoleRepository roleRepository,
            CampusRepository campusRepository,
            PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.roleRepository = roleRepository;
        this.campusRepository = campusRepository;
        this.passwordEncoder = passwordEncoder;
    }

    // ── GET /api/users/me ────────────────────────────────────────────────────

    /**
     * Returns the authenticated user's own profile.
     * Flutter uses this on the Profile screen and to refresh penalty/no-show
     * counts.
     */
    @GetMapping("/me")
    public User getMyProfile(Authentication auth) {
        return resolveUser(auth);
    }

    // ── PATCH /api/users/me/password ─────────────────────────────────────────

    /**
     * Changes the authenticated user's password.
     *
     * Request body:
     * { "currentPassword": "OldPass@123", "newPassword": "NewPass@456" }
     *
     * Rules:
     * - currentPassword must match the stored bcrypt hash
     * - newPassword minimum 8 characters
     * - newPassword cannot be the same as currentPassword
     */
    @PatchMapping("/me/password")
    public Map<String, String> changePassword(
            Authentication auth,
            @RequestBody Map<String, String> body) {

        User user = resolveUser(auth);

        String currentPassword = body.get("currentPassword");
        String newPassword = body.get("newPassword");

        if (currentPassword == null || currentPassword.isBlank()) {
            throw new ApiException("currentPassword is required", 400);
        }
        if (newPassword == null || newPassword.isBlank()) {
            throw new ApiException("newPassword is required", 400);
        }
        if (newPassword.length() < 8) {
            throw new ApiException("New password must be at least 8 characters", 400);
        }
        if (!passwordEncoder.matches(currentPassword, user.getPasswordHash())) {
            throw new ApiException("Current password is incorrect", 401);
        }
        if (passwordEncoder.matches(newPassword, user.getPasswordHash())) {
            throw new ApiException("New password must be different from the current password", 400);
        }

        user.setPasswordHash(passwordEncoder.encode(newPassword));
        userRepository.save(user);

        return Map.of("message", "Password changed successfully. Please log in again.");
    }

    // ── PATCH /api/users/me/profile ──────────────────────────────────────────

    /**
     * Updates display name and/or phone number.
     * Only provided fields are updated — omitted fields are unchanged.
     *
     * Request body (all optional):
     * { "fullName": "Rahul Sharma", "phone": "9876543210" }
     */
    @PatchMapping("/me/profile")
    public User updateMyProfile(
            Authentication auth,
            @RequestBody Map<String, String> body) {

        User user = resolveUser(auth);

        String fullName = body.get("fullName");
        String phone = body.get("phone");

        if (fullName != null && !fullName.isBlank()) {
            String trimmed = fullName.trim();
            if (trimmed.length() < 2 || trimmed.length() > 100) {
                throw new ApiException("Full name must be between 2 and 100 characters", 400);
            }
            user.setFullName(trimmed);
        }

        if (phone != null) {
            if (!phone.isBlank() && !phone.matches("^[6-9]\\d{9}$")) {
                throw new ApiException("Phone must be a valid 10-digit Indian mobile number starting with 6-9", 400);
            }
            user.setPhone(phone.isBlank() ? null : phone);
        }

        return userRepository.save(user);
    }

    /**
     * PATCH /api/users/fcm-token
     * Flutter calls this after login to register the device's FCM token.
     * Used later to send push notifications on order status changes.
     * Body: { "fcmToken": "eX..." }
     */
    @PatchMapping("/fcm-token")
    public Map<String, String> updateFcmToken(
            @RequestBody Map<String, String> body,
            Authentication auth) {
        User user = resolveUser(auth);
        user.setFcmToken(body.get("fcmToken"));
        userRepository.save(user);
        return Map.of("message", "FCM token registered successfully.");
    }

    // ── GET /api/users (SuperAdmin) ──────────────────────────────────────────

    @GetMapping
    public List<User> getAllUsers() {
        return userRepository.findAll();
    }

    // ── GET /api/users/campus/{campusId} (Admin / SuperAdmin) ────────────────

    /**
     * All users on a campus — useful for the campus admin dashboard
     * to see students, managers, and their penalty/account status.
     */
    @GetMapping("/campus/{campusId}")
    public List<User> getUsersByCampus(@PathVariable Long campusId) {
        return userRepository.findByCampusId(campusId);
    }

    // ── POST /api/users (SuperAdmin — manual user creation) ─────────────────

    @PostMapping
    public User createUser(@RequestBody UserRequest request) {

        Role role = roleRepository.findById(request.getRoleId())
                .orElseThrow(() -> new ApiException("Role not found", 404));

        Campus campus = campusRepository.findById(request.getCampusId())
                .orElseThrow(() -> new ApiException("Campus not found", 404));

        if (!request.getEmail().endsWith("@" + campus.getEmailDomain())) {
            throw new ApiException(
                    "Email must use the campus domain: @" + campus.getEmailDomain(), 400);
        }

        if (userRepository.findByEmail(request.getEmail()).isPresent()) {
            throw new ApiException("An account with this email already exists", 409);
        }

        User user = new User(
                request.getFullName(),
                request.getEmail(),
                passwordEncoder.encode(request.getPassword()),
                role,
                campus);

        return userRepository.save(user);
    }

    // ── Helper ────────────────────────────────────────────────────────────────

    private User resolveUser(Authentication auth) {
        String email = (String) auth.getPrincipal();
        return userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", 404));
    }
}