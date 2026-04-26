package com.smartcampus.backend.service;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpMethod;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * HTTP client for the Python FastAPI ML microservice (v2.0).
 *
 * <p>
 * All original methods are UNCHANGED. Five new methods have been added
 * following the exact same pattern: RestTemplate POST/GET, snake_case JSON,
 * graceful fallback when disabled or unreachable, timeout handling.
 *
 * <p>
 * application.yml settings:
 * 
 * <pre>
 * ml:
 *   service:
 *     url:        http://localhost:8000
 *     enabled:    true
 *     timeout-ms: 3000
 * </pre>
 *
 * <p>
 * Fallback values when ML service is disabled or unreachable:
 * <ul>
 * <li>predictDemandScore → 0.5 (existing)</li>
 * <li>getRecommendations → empty list</li>
 * <li>predictWaitTime → 20 minutes</li>
 * <li>getSlotDemandForecast → empty map</li>
 * <li>predictNoShowRisk → 0.5 (neutral)</li>
 * <li>getMenuPerformance → empty list</li>
 * </ul>
 */
@Component
public class MLClient {

    private static final Logger log = LoggerFactory.getLogger(MLClient.class);

    // ── Fallback constants ────────────────────────────────────────────────────
    static final double FALLBACK_SCORE = 0.5;
    static final int FALLBACK_WAIT_MINUTES = 20;
    static final double FALLBACK_NOSHOW_RISK = 0.5;

    // ── Endpoint paths ────────────────────────────────────────────────────────
    private static final String DEMAND_SCORE_PATH = "/predict/demand-score";
    private static final String RECOMMEND_PATH = "/recommend/food";
    private static final String WAIT_TIME_PATH = "/predict/wait-time";
    private static final String SLOT_FORECAST_PATH = "/forecast/slot-demand";
    private static final String NOSHOW_RISK_PATH = "/predict/no-show-risk";
    private static final String MENU_PERF_PATH = "/analytics/menu-performance";

    private static final DateTimeFormatter ISO = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

    private final RestTemplate restTemplate;

    @Value("${ml.service.url:http://localhost:8000}")
    private String mlServiceUrl;

    @Value("${ml.service.enabled:false}")
    private boolean enabled;

    public MLClient(
            @Value("${ml.service.timeout-ms:3000}") long timeoutMs,
            RestTemplateBuilder builder) {

        this.restTemplate = builder
                .connectTimeout(Duration.ofMillis(timeoutMs))
                .readTimeout(Duration.ofMillis(timeoutMs))
                .build();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // ORIGINAL METHOD — UNCHANGED
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Ask the ML service for a demand score for {@code menuItemId} at the
     * time represented by {@code expiresAt}.
     *
     * @return score ∈ [0.1, 0.9], or 0.5 on any failure
     */
    public double predictDemandScore(Long menuItemId, LocalDateTime expiresAt) {
        if (!enabled) {
            log.debug("[MLClient] disabled — returning fallback demand score");
            return FALLBACK_SCORE;
        }
        try {
            PredictDemandRequest body = new PredictDemandRequest(menuItemId, expiresAt.format(ISO));
            PredictDemandResponse response = restTemplate.postForObject(
                    mlServiceUrl + DEMAND_SCORE_PATH,
                    body,
                    PredictDemandResponse.class);
            if (response == null || response.demandScore == null) {
                log.warn("[MLClient] null response from demand-score — using fallback");
                return FALLBACK_SCORE;
            }
            log.info("[MLClient] demand item={} score={} strategy={}",
                    menuItemId, response.demandScore, response.strategy);
            return response.demandScore;
        } catch (Exception ex) {
            log.warn("[MLClient] demand-score call failed ({}): {} — fallback {}",
                    ex.getClass().getSimpleName(), ex.getMessage(), FALLBACK_SCORE);
            return FALLBACK_SCORE;
        }
    }

    /**
     * Ping the ML service health endpoint.
     */
    public boolean isHealthy() {
        if (!enabled)
            return false;
        try {
            restTemplate.getForObject(mlServiceUrl + "/health", String.class);
            return true;
        } catch (Exception ex) {
            return false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NEW METHOD 1 — Personalised Food Recommendations
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Get personalised food item recommendations for a student at a specific
     * outlet.
     *
     * <p>
     * Called when a student opens an outlet menu page. The returned IDs should be
     * used to display a "Recommended for You" section at the top of the menu.
     *
     * <p>
     * Cold start behaviour: for new users or when ML service is down, the Python
     * service itself falls back to popularity-based recommendations. The Java side
     * sees the same response shape either way.
     *
     * @param userId   The logged-in student's ID
     * @param outletId The outlet being browsed
     * @param campusId The campus (recommendations are campus-scoped)
     * @return List of recommended menu item IDs (up to 5), ordered by relevance.
     *         Returns empty list on any failure — caller should skip the section.
     */
    public List<Long> getRecommendations(Long userId, Long outletId, Long campusId) {
        if (!enabled) {
            log.debug("[MLClient] disabled — returning empty recommendations");
            return Collections.emptyList();
        }
        try {
            RecommendRequest body = new RecommendRequest(userId, outletId, campusId, 5);
            RecommendResponse response = restTemplate.postForObject(
                    mlServiceUrl + RECOMMEND_PATH,
                    body,
                    RecommendResponse.class);
            if (response == null || response.recommendations == null) {
                return Collections.emptyList();
            }
            List<Long> ids = response.recommendations.stream()
                    .map(r -> r.menuItemId)
                    .toList();
            log.info("[MLClient] recommendations user={} outlet={} → {} items strategy={}",
                    userId, outletId, ids.size(), response.strategy);
            return ids;
        } catch (Exception ex) {
            log.warn("[MLClient] getRecommendations failed ({}): {} — returning empty list",
                    ex.getClass().getSimpleName(), ex.getMessage());
            return Collections.emptyList();
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NEW METHOD 2 — Dynamic Wait Time Prediction
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Predict estimated wait time in minutes for an order about to be placed.
     *
     * <p>
     * Call this in OrderService just before creating the order, to set the
     * {@code readyAt} field dynamically instead of using a fixed offset.
     *
     * <p>
     * Example:
     * 
     * <pre>
     * int waitMinutes = mlClient.predictWaitTime(outletId, itemCount, activeOrders);
     * LocalDateTime readyAt = LocalDateTime.now().plusMinutes(waitMinutes);
     * </pre>
     *
     * @param outletId     The outlet receiving the order
     * @param itemCount    Number of items in the order
     * @param activeOrders Current number of PLACED + PREPARING orders at outlet.
     *                     Pass -1 to let the ML service fetch this from DB.
     * @return Estimated wait time in minutes. Fallback:
     *         {@value FALLBACK_WAIT_MINUTES}.
     */
    public int predictWaitTime(Long outletId, int itemCount, int activeOrders) {
        if (!enabled) {
            log.debug("[MLClient] disabled — returning fallback wait time {}min", FALLBACK_WAIT_MINUTES);
            return FALLBACK_WAIT_MINUTES;
        }
        try {
            WaitTimeRequest body = new WaitTimeRequest(outletId, itemCount, activeOrders, -1, -1);
            WaitTimeResponse response = restTemplate.postForObject(
                    mlServiceUrl + WAIT_TIME_PATH,
                    body,
                    WaitTimeResponse.class);
            if (response == null || response.estimatedMinutes == null) {
                log.warn("[MLClient] null response from wait-time — using fallback");
                return FALLBACK_WAIT_MINUTES;
            }
            log.info("[MLClient] wait-time outlet={} items={} queue={} → {}min strategy={}",
                    outletId, itemCount, activeOrders, response.estimatedMinutes, response.strategy);
            return response.estimatedMinutes;
        } catch (Exception ex) {
            log.warn("[MLClient] predictWaitTime failed ({}): {} — fallback {}min",
                    ex.getClass().getSimpleName(), ex.getMessage(), FALLBACK_WAIT_MINUTES);
            return FALLBACK_WAIT_MINUTES;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NEW METHOD 3 — Slot Demand Forecast
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Get predicted order volume per hour for a specific date at an outlet.
     *
     * <p>
     * Used by the manager dashboard to decide slot capacities in advance.
     * The map key is the hour of day (0–23), value is predicted order count.
     *
     * @param outletId The outlet to forecast for
     * @param date     The date to forecast (typically tomorrow or a future date)
     * @return Map of hour → predicted order count. Empty map on failure.
     */
    public Map<Integer, Integer> getSlotDemandForecast(Long outletId, LocalDate date) {
        if (!enabled) {
            log.debug("[MLClient] disabled — returning empty slot forecast");
            return Collections.emptyMap();
        }
        try {
            String url = String.format(
                    "%s%s?outletId=%d&date=%s",
                    mlServiceUrl, SLOT_FORECAST_PATH, outletId, date.toString());
            SlotForecastResponse response = restTemplate.getForObject(url, SlotForecastResponse.class);
            if (response == null || response.hourlyForecast == null) {
                return Collections.emptyMap();
            }
            Map<Integer, Integer> result = new java.util.HashMap<>();
            for (HourlyForecast entry : response.hourlyForecast) {
                result.put(entry.hour, entry.predictedOrders);
            }
            log.info("[MLClient] slot-forecast outlet={} date={} → {} hours strategy={}",
                    outletId, date, result.size(), response.strategy);
            return result;
        } catch (Exception ex) {
            log.warn("[MLClient] getSlotDemandForecast failed ({}): {} — returning empty map",
                    ex.getClass().getSimpleName(), ex.getMessage());
            return Collections.emptyMap();
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NEW METHOD 4 — No-Show Risk Prediction
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Predict the probability that a student will not pick up their order.
     *
     * <p>
     * Call this after order creation. If risk ≥ 0.65 (HIGH), consider:
     * <ul>
     * <li>Requiring advance payment (block COD for this order)</li>
     * <li>Alerting the manager via NotificationService</li>
     * </ul>
     *
     * <p>
     * Only call for PLATFORM orders — COUNTER orders have no registered user
     * and are always assumed to be picked up immediately.
     *
     * @param userId   The student's user ID
     * @param amount   The order's total amount in ₹
     * @param slotHour The pickup slot hour (0–23)
     * @return No-show probability ∈ [0, 1]. Fallback:
     *         {@value FALLBACK_NOSHOW_RISK}.
     */
    public double predictNoShowRisk(Long userId, double amount, int slotHour) {
        if (!enabled) {
            log.debug("[MLClient] disabled — returning fallback no-show risk {}", FALLBACK_NOSHOW_RISK);
            return FALLBACK_NOSHOW_RISK;
        }
        try {
            NoShowRiskRequest body = new NoShowRiskRequest(userId, amount, slotHour, 30);
            NoShowRiskResponse response = restTemplate.postForObject(
                    mlServiceUrl + NOSHOW_RISK_PATH,
                    body,
                    NoShowRiskResponse.class);
            if (response == null || response.noShowProbability == null) {
                log.warn("[MLClient] null response from no-show risk — using fallback");
                return FALLBACK_NOSHOW_RISK;
            }
            log.info("[MLClient] no-show user={} risk={} level={} strategy={}",
                    userId, response.noShowProbability, response.riskLevel, response.strategy);
            return response.noShowProbability;
        } catch (Exception ex) {
            log.warn("[MLClient] predictNoShowRisk failed ({}): {} — fallback {}",
                    ex.getClass().getSimpleName(), ex.getMessage(), FALLBACK_NOSHOW_RISK);
            return FALLBACK_NOSHOW_RISK;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NEW METHOD 5 — Menu Item Performance Analytics
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Get ML-powered performance analytics for all items in an outlet's menu.
     *
     * <p>
     * Each map in the returned list contains:
     * <ul>
     * <li>{@code menuItemId} — Long</li>
     * <li>{@code itemName} — String</li>
     * <li>{@code orderFrequency} — Double (0–1)</li>
     * <li>{@code revenueContribution}— Double (0–1)</li>
     * <li>{@code trend} — String: RISING | STABLE | FALLING</li>
     * <li>{@code suggestion} — String: actionable text for manager</li>
     * </ul>
     *
     * @param outletId The outlet whose menu to analyse
     * @return List of per-item analytics maps. Empty list on failure.
     */
    public List<Map<String, Object>> getMenuPerformance(Long outletId) {
        if (!enabled) {
            log.debug("[MLClient] disabled — returning empty menu performance");
            return Collections.emptyList();
        }
        try {
            String url = String.format(
                    "%s%s?outletId=%d",
                    mlServiceUrl, MENU_PERF_PATH, outletId);
            MenuPerformanceResponse response = restTemplate.getForObject(
                    url, MenuPerformanceResponse.class);
            if (response == null || response.items == null) {
                return Collections.emptyList();
            }
            log.info("[MLClient] menu-performance outlet={} → {} items",
                    outletId, response.items.size());
            // Convert each ItemPerformance to a generic Map for the controller layer
            return response.items.stream()
                    .map(item -> {
                        Map<String, Object> m = new java.util.LinkedHashMap<>();
                        m.put("menuItemId", item.menuItemId);
                        m.put("itemName", item.itemName);
                        m.put("orderFrequency", item.orderFrequency);
                        m.put("revenueContribution", item.revenueContribution);
                        m.put("totalOrders", item.totalOrders);
                        m.put("trend", item.trend);
                        m.put("suggestion", item.suggestion);
                        return m;
                    })
                    .toList();
        } catch (Exception ex) {
            log.warn("[MLClient] getMenuPerformance failed ({}): {} — returning empty list",
                    ex.getClass().getSimpleName(), ex.getMessage());
            return Collections.emptyList();
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // INTERNAL DTOs — ML service speaks snake_case JSON
    // ═══════════════════════════════════════════════════════════════════════════

    // ── Demand score (original, unchanged) ────────────────────────────────────

    private record PredictDemandRequest(
            @JsonProperty("menu_item_id") Long menuItemId,
            @JsonProperty("expires_at") String expiresAt) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private static class PredictDemandResponse {
        @JsonProperty("demand_score")
        Double demandScore;
        @JsonProperty("penalty")
        Double penalty;
        @JsonProperty("strategy")
        String strategy;
        @JsonProperty("confidence")
        String confidence;
    }

    // ── Recommendations ────────────────────────────────────────────────────────

    private record RecommendRequest(
            @JsonProperty("userId") Long userId,
            @JsonProperty("outletId") Long outletId,
            @JsonProperty("campusId") Long campusId,
            @JsonProperty("limit") int limit) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private static class RecommendResponse {
        @JsonProperty("recommendations")
        List<RecommendedItem> recommendations;
        @JsonProperty("strategy")
        String strategy;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private static class RecommendedItem {
        @JsonProperty("menuItemId")
        Long menuItemId;
        @JsonProperty("score")
        Double score;
        @JsonProperty("reason")
        String reason;
    }

    // ── Wait time ─────────────────────────────────────────────────────────────

    private record WaitTimeRequest(
            @JsonProperty("outletId") Long outletId,
            @JsonProperty("orderItemCount") int orderItemCount,
            @JsonProperty("currentActiveOrders") int currentActiveOrders,
            @JsonProperty("hourOfDay") int hourOfDay,
            @JsonProperty("dayOfWeek") int dayOfWeek) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private static class WaitTimeResponse {
        @JsonProperty("estimatedMinutes")
        Integer estimatedMinutes;
        @JsonProperty("confidenceInterval")
        List<Integer> confidenceInterval;
        @JsonProperty("strategy")
        String strategy;
    }

    // ── Slot demand forecast ──────────────────────────────────────────────────

    @JsonIgnoreProperties(ignoreUnknown = true)
    private static class SlotForecastResponse {
        @JsonProperty("outletId")
        Long outletId;
        @JsonProperty("date")
        String date;
        @JsonProperty("hourlyForecast")
        List<HourlyForecast> hourlyForecast;
        @JsonProperty("strategy")
        String strategy;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private static class HourlyForecast {
        @JsonProperty("hour")
        Integer hour;
        @JsonProperty("predictedOrders")
        Integer predictedOrders;
        @JsonProperty("suggestedSlotCapacity")
        Integer suggestedSlotCapacity;
    }

    // ── No-show risk ──────────────────────────────────────────────────────────

    private record NoShowRiskRequest(
            @JsonProperty("userId") Long userId,
            @JsonProperty("orderAmount") double orderAmount,
            @JsonProperty("slotHour") int slotHour,
            @JsonProperty("minutesUntilSlot") int minutesUntilSlot) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private static class NoShowRiskResponse {
        @JsonProperty("noShowProbability")
        Double noShowProbability;
        @JsonProperty("riskLevel")
        String riskLevel;
        @JsonProperty("recommendation")
        String recommendation;
        @JsonProperty("strategy")
        String strategy;
    }

    // ── Menu performance ──────────────────────────────────────────────────────

    @JsonIgnoreProperties(ignoreUnknown = true)
    private static class MenuPerformanceResponse {
        @JsonProperty("outletId")
        Long outletId;
        @JsonProperty("items")
        List<ItemPerformance> items;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private static class ItemPerformance {
        @JsonProperty("menuItemId")
        Long menuItemId;
        @JsonProperty("itemName")
        String itemName;
        @JsonProperty("orderFrequency")
        Double orderFrequency;
        @JsonProperty("revenueContribution")
        Double revenueContribution;
        @JsonProperty("totalOrders")
        Integer totalOrders;
        @JsonProperty("trend")
        String trend;
        @JsonProperty("suggestion")
        String suggestion;
    }
}