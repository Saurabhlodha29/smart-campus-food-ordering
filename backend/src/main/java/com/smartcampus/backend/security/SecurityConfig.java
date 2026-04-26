package com.smartcampus.backend.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;
import java.util.List;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final JwtFilter jwtFilter;

    public SecurityConfig(JwtFilter jwtFilter) {
        this.jwtFilter = jwtFilter;
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth

                        // ── Public ──────────────────────────────────────────────────
                        .requestMatchers("/api/auth/**").permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/admin-applications").permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/outlet-applications").permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/payments/webhook/razorpay").permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/payments/order/**").permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/campuses").permitAll()
                        .requestMatchers("/test-pay.html").permitAll()

                        // ── SuperAdmin ───────────────────────────────────────────────
                        .requestMatchers(HttpMethod.POST, "/api/campuses").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/campuses/*/deactivate").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/campuses/*/reactivate").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/admin-applications").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/admin-applications/all").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.PATCH, "/api/admin-applications/*/approve").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.PATCH, "/api/admin-applications/*/reject").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/outlet-applications/platform-pending")
                        .hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/payouts/all").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/payouts/outlet/*").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/payouts/failed").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/payouts/*/retry").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/payouts/summary/*").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/outlets/all").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/orders").hasAnyRole("SUPERADMIN", "ADMIN")

                        // ── Admin ────────────────────────────────────────────────────
                        .requestMatchers(HttpMethod.GET, "/api/outlet-applications/pending").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/outlet-applications/all").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/outlet-applications/*/verification-report")
                        .hasRole("ADMIN")
                        .requestMatchers(HttpMethod.PATCH, "/api/outlet-applications/*/approve").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.PATCH, "/api/outlet-applications/*/reject").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/outlets/campus/*/all").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/outlets/*/suspend").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/outlets/*/reactivate").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.DELETE, "/api/outlets/*").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/menu-items/all").hasAnyRole("MANAGER", "ADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/payouts/campus").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/penalties/*/waive").hasRole("ADMIN")

                        // ── Manager ──────────────────────────────────────────────────
                        .requestMatchers(HttpMethod.GET, "/api/outlets/mine").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.POST, "/api/outlets/*/launch").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.POST, "/api/outlets/*/toggle").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.POST, "/api/menu-items").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.PATCH, "/api/menu-items/*").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.DELETE, "/api/menu-items/*").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.PATCH, "/api/orders/*/status").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.POST, "/api/orders/*/pickup").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.GET, "/api/orders/outlet/*").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.GET, "/api/payouts/my-outlet").hasRole("MANAGER")
                        // FIXED: was incorrectly mapped to /api/outlets/ in old config
                        .requestMatchers(HttpMethod.PATCH, "/api/payouts/mine/bank-details").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.POST, "/api/slots").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.DELETE, "/api/slots/*").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.POST, "/api/manager/orders/counter").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.GET,  "/api/manager/orders/ledger").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.GET,  "/api/manager/orders/ledger/summary").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.PATCH, "/api/slots/*/adjust-count").hasRole("MANAGER")
                        .requestMatchers(HttpMethod.PATCH, "/api/slots/*/capacity").hasRole("MANAGER")

                        // ── Student ──────────────────────────────────────────────────
                        .requestMatchers(HttpMethod.POST, "/api/orders").hasRole("STUDENT")
                        .requestMatchers(HttpMethod.GET, "/api/orders/student/*").hasRole("STUDENT")
                        // Student can cancel their own PLACED orders
                        .requestMatchers(HttpMethod.POST, "/api/orders/*/cancel").hasRole("STUDENT")
                        .requestMatchers(HttpMethod.POST, "/api/payments/initiate/order/*").hasRole("STUDENT")
                        .requestMatchers(HttpMethod.POST, "/api/payments/verify/order").hasRole("STUDENT")
                        .requestMatchers(HttpMethod.POST, "/api/payments/initiate/penalty/*").hasRole("STUDENT")
                        .requestMatchers(HttpMethod.POST, "/api/payments/verify/penalty").hasRole("STUDENT")

                        // ── Any authenticated user ───────────────────────────────────
                        .requestMatchers(HttpMethod.GET, "/api/users/me").authenticated()
                        .requestMatchers(HttpMethod.PATCH, "/api/users/me/password").authenticated()
                        .requestMatchers(HttpMethod.PATCH, "/api/users/me/profile").authenticated()
                        .requestMatchers(HttpMethod.GET, "/api/users/campus/*").hasAnyRole("ADMIN", "SUPERADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/users").hasRole("SUPERADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/payments/refund/order/*")
                        .hasAnyRole("ADMIN", "SUPERADMIN")
                        .requestMatchers(HttpMethod.GET, "/api/campuses/*").authenticated()
                        .requestMatchers(HttpMethod.GET, "/api/outlets/*").authenticated()
                        .requestMatchers(HttpMethod.GET, "/api/outlets/campus/*").authenticated()
                        .requestMatchers(HttpMethod.GET, "/api/menu-items").authenticated()
                        .requestMatchers(HttpMethod.GET, "/api/orders/*").authenticated()
                        .requestMatchers(HttpMethod.GET, "/api/payments/order/*").authenticated()
                        .requestMatchers("/api/notifications/**").authenticated()
                        .requestMatchers("/api/penalties/**").authenticated()
                        .requestMatchers(HttpMethod.GET, "/api/slots").authenticated()

                        .anyRequest().authenticated())
                .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOriginPatterns(List.of("*"));
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(Arrays.asList("authorization", "content-type", "x-auth-token"));
        configuration.setExposedHeaders(List.of("x-auth-token"));
        configuration.setAllowCredentials(true);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}