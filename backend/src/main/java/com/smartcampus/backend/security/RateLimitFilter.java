package com.smartcampus.backend.security;

import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/**
 * User-level rate limiter. 100 authenticated requests per user per 60 seconds.
 *
 * Uses the JWT subject email as the key. Redis makes the limit work across
 * multiple backend instances; the in-memory map is only a fallback if Redis is
 * temporarily unavailable.
 */
@Component
@Order(1)
public class RateLimitFilter implements Filter {

    private static final int MAX_REQUESTS = 100;
    private static final long WINDOW_MS = 60_000L;
    private static final long WINDOW_SECONDS = 60L;

    private final Map<String, long[]> fallbackCounters = new ConcurrentHashMap<>();
    private final JwtUtil jwtUtil;
    private final StringRedisTemplate redis;

    public RateLimitFilter(JwtUtil jwtUtil, StringRedisTemplate redis) {
        this.jwtUtil = jwtUtil;
        this.redis = redis;
    }

    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest request = (HttpServletRequest) req;
        HttpServletResponse response = (HttpServletResponse) res;

        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            chain.doFilter(req, res);
            return;
        }

        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            chain.doFilter(req, res);
            return;
        }

        String token = authHeader.substring(7);
        String email;
        try {
            email = jwtUtil.extractEmail(token);
        } catch (Exception e) {
            chain.doFilter(req, res);
            return;
        }

        if (isRateLimited(email)) {
            response.setStatus(429);
            response.setContentType("application/json");
            response.getWriter().write("{\"message\":\"Too many requests. Limit: "
                    + MAX_REQUESTS + " per minute.\",\"status\":429}");
            return;
        }

        chain.doFilter(req, res);
    }

    private boolean isRateLimited(String email) {
        try {
            String key = "rate:" + email;
            Long count = redis.opsForValue().increment(key);
            if (count != null && count == 1L) {
                redis.expire(key, WINDOW_SECONDS, TimeUnit.SECONDS);
            }
            return count != null && count > MAX_REQUESTS;
        } catch (RuntimeException e) {
            return isRateLimitedInMemory(email);
        }
    }

    private boolean isRateLimitedInMemory(String email) {
        long now = Instant.now().toEpochMilli();
        long[] window = fallbackCounters.compute(email, (key, current) -> {
            if (current == null || now - current[1] > WINDOW_MS) {
                return new long[] { 1, now };
            }
            current[0]++;
            return current;
        });
        return window[0] > MAX_REQUESTS;
    }
}
