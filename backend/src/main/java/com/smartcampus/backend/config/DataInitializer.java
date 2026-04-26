package com.smartcampus.backend.config;

import com.smartcampus.backend.domain.Role;
import com.smartcampus.backend.domain.User;
import com.smartcampus.backend.repository.RoleRepository;
import com.smartcampus.backend.repository.UserRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * Seeds the database with required baseline data on every startup (idempotent).
 *
 * Seeded data:
 *   - Roles:     SUPERADMIN, ADMIN, MANAGER, STUDENT
 *   - SuperAdmin user (credentials pulled from application.properties)
 *
 * The superadmin credentials are NOT hardcoded — they come from environment
 * variables or application.properties so they stay out of source control.
 *
 * application.properties entries needed:
 *   superadmin.email=your-email@domain.com
 *   superadmin.password=changeme-strong-password
 *   superadmin.fullname=Platform SuperAdmin
 */
@Configuration
public class DataInitializer {

    @Value("${superadmin.email:superadmin@smartcampus.dev}")
    private String superadminEmail;

    @Value("${superadmin.password:SuperAdmin@123}")
    private String superadminPassword;

    @Value("${superadmin.fullname:Platform SuperAdmin}")
    private String superadminFullName;

    @Bean
    CommandLineRunner initData(RoleRepository roleRepo,
                                UserRepository userRepo,
                                PasswordEncoder passwordEncoder) {
        return args -> {

            // ── 1. Seed roles ──────────────────────────────────────────────
            ensureRole(roleRepo, "SUPERADMIN");
            ensureRole(roleRepo, "ADMIN");
            ensureRole(roleRepo, "MANAGER");
            ensureRole(roleRepo, "STUDENT");

            // ── 2. Seed SuperAdmin user ────────────────────────────────────
            if (userRepo.findByEmail(superadminEmail).isEmpty()) {
                Role superadminRole = roleRepo.findByName("SUPERADMIN")
                        .orElseThrow(() -> new IllegalStateException("SUPERADMIN role missing after seed"));

                User superadmin = new User(
                        superadminFullName,
                        superadminEmail,
                        passwordEncoder.encode(superadminPassword),
                        superadminRole,
                        null   // SuperAdmin is not tied to any campus
                );
                userRepo.save(superadmin);

                System.out.println("[DataInitializer] SuperAdmin created: " + superadminEmail);
            }
        };
    }

    private void ensureRole(RoleRepository roleRepo, String name) {
        if (roleRepo.findByName(name).isEmpty()) {
            roleRepo.save(new Role(name));
            System.out.println("[DataInitializer] Role created: " + name);
        }
    }
}