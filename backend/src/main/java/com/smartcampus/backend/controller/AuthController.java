package com.smartcampus.backend.controller;

import com.smartcampus.backend.domain.Campus;
import com.smartcampus.backend.domain.Role;
import com.smartcampus.backend.domain.User;
import com.smartcampus.backend.dto.AuthRequest;
import com.smartcampus.backend.dto.RegisterRequest;
import com.smartcampus.backend.dto.VerifyEmailRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.CampusRepository;
import com.smartcampus.backend.repository.RoleRepository;
import com.smartcampus.backend.repository.UserRepository;
import com.smartcampus.backend.security.JwtUtil;
import com.smartcampus.backend.service.OtpService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UserRepository userRepo;
    private final RoleRepository roleRepo;
    private final CampusRepository campusRepo;
    private final JwtUtil jwtUtil;
    private final PasswordEncoder passwordEncoder;
    private final OtpService otpService;

    public AuthController(UserRepository userRepo,
            RoleRepository roleRepo,
            CampusRepository campusRepo,
            JwtUtil jwtUtil,
            PasswordEncoder passwordEncoder,
            OtpService otpService) {
        this.userRepo = userRepo;
        this.roleRepo = roleRepo;
        this.campusRepo = campusRepo;
        this.jwtUtil = jwtUtil;
        this.passwordEncoder = passwordEncoder;
        this.otpService = otpService;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // POST /api/auth/login
    // ─────────────────────────────────────────────────────────────────────────

    @PostMapping("/login")
    public Map<String, String> login(@RequestBody AuthRequest request) {

        User user = userRepo.findByEmail(request.getEmail())
                .orElseThrow(() -> new ApiException("Invalid email or password", 401));

        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new ApiException("Invalid email or password", 401);
        }

        // Specifically guard against unverified accounts trying to log in
        if ("PENDING_VERIFICATION".equals(user.getAccountStatus())) {
            throw new ApiException(
                    "Email not verified. Please check your inbox for the OTP, " +
                            "or use /api/auth/resend-otp to get a new one.",
                    403);
        }

        if (!("ACTIVE".equals(user.getAccountStatus()))) {
            throw new ApiException("Your account is " + user.getAccountStatus()
                    + ". Please contact support.", 403);
        }

        String token = jwtUtil.generateToken(user.getEmail(), user.getRole().getName());

        Map<String, String> response = new HashMap<>();
        response.put("token", token);
        response.put("role", user.getRole().getName());
        response.put("name", user.getFullName());
        response.put("email", user.getEmail());
        response.put("id", String.valueOf(user.getId()));
        response.put("accountStatus", user.getAccountStatus());
        response.put("pendingPenalty", String.valueOf(user.getPendingPenaltyAmount()));
        response.put("noShowCount", String.valueOf(user.getNoShowCount()));

        if (user.getCampus() != null) {
            response.put("campusId", String.valueOf(user.getCampus().getId()));
            response.put("campusName", user.getCampus().getName());
        }

        return response;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // POST /api/auth/register — Step 1 of 2: create account, send OTP
    //
    // IMPORTANT CHANGE from old version:
    // - Account is saved with status = "PENDING_VERIFICATION"
    // - NO JWT is returned here — user cannot access the app yet
    // - OTP is generated and emailed
    // ─────────────────────────────────────────────────────────────────────────

    @PostMapping("/register")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, String> register(@Valid @RequestBody RegisterRequest request) {

        String email = request.getEmail().toLowerCase().trim();

        // 1. Duplicate check — but handle the case where someone registered
        // but never verified (allow them to re-register / resend OTP)
        userRepo.findByEmail(email).ifPresent(existing -> {
            if ("PENDING_VERIFICATION".equals(existing.getAccountStatus())) {
                // Account exists but is unverified — resend OTP and tell user
                otpService.generateAndSendOtp(email, existing.getFullName());
                throw new ApiException(
                        "Account already exists but email is not verified. " +
                                "A new OTP has been sent to " + email + ".",
                        409);
            }
            throw new ApiException("An account with this email already exists.", 409);
        });

        // 2. Campus lookup by email domain
        String domain = email.substring(email.indexOf('@') + 1);
        Campus campus = campusRepo.findByEmailDomain(domain)
                .orElseThrow(() -> new ApiException(
                        "No registered campus found for email domain '@" + domain + "'. "
                                + "Your campus may not be on the platform yet.",
                        404));

        // 3. Campus must be active
        if (!"ACTIVE".equals(campus.getStatus())) {
            throw new ApiException("The campus for your email domain is not currently active.", 403);
        }

        // 4. Assign STUDENT role
        Role studentRole = roleRepo.findByName("STUDENT")
                .orElseThrow(() -> new ApiException("STUDENT role not seeded — contact support.", 500));

        // 5. Create user with PENDING_VERIFICATION status (not ACTIVE yet)
        User student = new User(
                request.getFullName(),
                email,
                passwordEncoder.encode(request.getPassword()),
                studentRole,
                campus);
        student.setAccountStatus("PENDING_VERIFICATION");
        userRepo.save(student);

        // 6. Generate OTP and email it (async — returns immediately)
        otpService.generateAndSendOtp(email, request.getFullName());

        // 7. Return minimal response — NO token until email is verified
        return Map.of(
                "message", "Registration successful! Please check " + email + " for your 6-digit OTP.",
                "email", email,
                "status", "PENDING_VERIFICATION");
    }

    // ─────────────────────────────────────────────────────────────────────────
    // POST /api/auth/verify-email — Step 2 of 2: submit OTP, get JWT
    //
    // Body: { "email": "student@college.edu", "otp": "847291" }
    // Returns: Full login response with JWT token (same as /login)
    // ─────────────────────────────────────────────────────────────────────────

    @PostMapping("/verify-email")
    public Map<String, String> verifyEmail(@Valid @RequestBody VerifyEmailRequest request) {

        String email = request.getEmail().toLowerCase().trim();

        // 1. Load the user — must exist and be pending verification
        User user = userRepo.findByEmail(email)
                .orElseThrow(() -> new ApiException("No account found for this email.", 404));

        if (!"PENDING_VERIFICATION".equals(user.getAccountStatus())) {
            if ("ACTIVE".equals(user.getAccountStatus())) {
                throw new ApiException("Email is already verified. Please log in.", 400);
            }
            throw new ApiException("Account cannot be verified in its current state. Contact support.", 403);
        }

        // 2. Validate the OTP (throws ApiException if invalid or expired)
        otpService.validateOtp(email, request.getOtp());

        // 3. Activate the account
        user.setAccountStatus("ACTIVE");
        userRepo.save(user);

        // 4. Issue JWT — user is now fully logged in
        String token = jwtUtil.generateToken(user.getEmail(), user.getRole().getName());

        Map<String, String> response = new HashMap<>();
        response.put("token", token);
        response.put("role", user.getRole().getName());
        response.put("name", user.getFullName());
        response.put("email", user.getEmail());
        response.put("id", String.valueOf(user.getId()));
        response.put("accountStatus", "ACTIVE");
        response.put("pendingPenalty", String.valueOf(user.getPendingPenaltyAmount()));
        response.put("noShowCount", String.valueOf(user.getNoShowCount()));

        if (user.getCampus() != null) {
            response.put("campusId", String.valueOf(user.getCampus().getId()));
            response.put("campusName", user.getCampus().getName());
        }

        return response;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // POST /api/auth/resend-otp
    //
    // Called when user says "I didn't receive the OTP" or it expired.
    // Body: { "email": "student@college.edu" }
    // Rate limiting: handled by OtpService deleting old tokens before creating new
    // one.
    // ─────────────────────────────────────────────────────────────────────────

    @PostMapping("/resend-otp")
    public Map<String, String> resendOtp(@RequestBody Map<String, String> body) {

        String email = body.getOrDefault("email", "").toLowerCase().trim();
        if (email.isBlank()) {
            throw new ApiException("Email is required.", 400);
        }

        User user = userRepo.findByEmail(email)
                .orElseThrow(() -> new ApiException("No account found for this email.", 404));

        if (!"PENDING_VERIFICATION".equals(user.getAccountStatus())) {
            throw new ApiException("This account does not need OTP verification.", 400);
        }

        // Delete old OTP and send a fresh one
        otpService.generateAndSendOtp(email, user.getFullName());

        return Map.of(
                "message", "A new OTP has been sent to " + email + ".");
    }
}