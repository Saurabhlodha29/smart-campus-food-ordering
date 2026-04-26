package com.smartcampus.backend.service;

import com.smartcampus.backend.domain.Notification;
import com.smartcampus.backend.domain.Order;
import com.smartcampus.backend.domain.OrderItem;
import com.smartcampus.backend.domain.User;
import com.smartcampus.backend.repository.NotificationRepository;
import com.smartcampus.backend.repository.OrderItemRepository;
import com.smartcampus.backend.repository.OrderRepository;
import com.smartcampus.backend.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

/**
 * Handles expired orders and applies demand-based penalties.
 *
 * <h3>Penalty logic (CRITICAL FIX)</h3>
 * A penalty is ONLY charged when:
 * <ol>
 * <li>The order reached <b>READY</b> status — i.e. the outlet actually prepared
 * the food.</li>
 * <li>The student did NOT pick it up within the grace window (expiresAt has
 * passed).</li>
 * </ol>
 * Orders still in PLACED or PREPARING when expiresAt passes are marked EXPIRED
 * but NO penalty is charged — the outlet never finished preparing so the
 * student
 * could not have picked it up.
 *
 * <h3>Demand-score strategy (priority order)</h3>
 * <ol>
 * <li><b>ML service</b> — Python FastAPI ({@code MLClient}) when
 * {@code ml.service.enabled=true} and the service is reachable.</li>
 * <li><b>Rule-based</b> — the original Java window query; always
 * available.</li>
 * </ol>
 *
 * <h3>Scheduled</h3>
 * Runs every 5 minutes ({@code fixedRate = 300_000 ms}).
 */
@Service
public class PenaltyService {

    private static final Logger log = LoggerFactory.getLogger(PenaltyService.class);

    private static final double BASE_PENALTY = 50.0;
    private static final int WINDOW_MINUTES = 45;
    private static final int LOOKBACK_DAYS = 10;

    private final OrderRepository orderRepository;
    private final OrderItemRepository orderItemRepository;
    private final UserRepository userRepository;
    private final MLClient mlClient;
    private final NotificationRepository notificationRepository;

    public PenaltyService(OrderRepository orderRepository,
            OrderItemRepository orderItemRepository,
            UserRepository userRepository,
            MLClient mlClient,
            NotificationRepository notificationRepository) {

        this.orderRepository = orderRepository;
        this.orderItemRepository = orderItemRepository;
        this.userRepository = userRepository;
        this.mlClient = mlClient;
        this.notificationRepository = notificationRepository;
    }

    // ── Scheduled job ─────────────────────────────────────────────────────────

    @Scheduled(fixedRate = 300_000) // every 5 minutes
    @Transactional
    public void processExpiredOrders() {

        LocalDateTime now = LocalDateTime.now();

        // ── FIX 1: Expire orders that are PLACED/PREPARING past their expiry ──
        // These are NOT penalised — the manager never finished preparing, so
        // the student had no opportunity to pick up. Just mark EXPIRED.
        List<Order> abandonedByOutlet = orderRepository.findByStatusInAndExpiresAtBefore(
                List.of("PLACED", "PREPARING"), now);

        if (!abandonedByOutlet.isEmpty()) {
            log.info("[PenaltyService] Expiring {} order(s) that never reached READY (no penalty).",
                    abandonedByOutlet.size());
        }

        for (Order order : abandonedByOutlet) {
            order.setStatus("EXPIRED");
            orderRepository.save(order);
            log.info("[PenaltyService] Order #{} expired (was {}) — outlet did not prepare in time. No penalty.",
                    order.getId(), order.getStatus());
        }

        // ── FIX 2: Penalise only orders that reached READY but were not picked ──
        // These are genuine no-shows — food was ready, student didn't come.
        List<Order> noShows = orderRepository.findByStatusAndExpiresAtBefore("READY", now);

        if (!noShows.isEmpty()) {
            log.info("[PenaltyService] Processing {} no-show order(s) (penalty will be charged).",
                    noShows.size());
        }

        for (Order order : noShows) {
            processNoShow(order, now);
        }
    }

    // ── Core logic ────────────────────────────────────────────────────────────

    /**
     * Called only for orders that were READY and not picked up — a genuine no-show.
     * Marks the order EXPIRED and charges the student a demand-weighted penalty.
     */
    private void processNoShow(Order order, LocalDateTime now) {

        // STEP 1: Mark order EXPIRED
        order.setStatus("EXPIRED");
        orderRepository.save(order);

        // STEP 2: Load items
        List<OrderItem> items = orderItemRepository.findByOrderId(order.getId());
        if (items.isEmpty()) {
            log.warn("[PenaltyService] Order #{} has no items — skipping penalty.", order.getId());
            return;
        }

        // STEP 3: Demand score per item — ML first, rule-based fallback
        double totalDemandScore = 0.0;
        for (OrderItem item : items) {
            double score = getDemandScore(item.getMenuItem().getId(), order.getExpiresAt());
            totalDemandScore += score;
        }
        double avgDemandScore = totalDemandScore / items.size();

        // STEP 4: Penalty
        // Higher demand → lower penalty (outlet can resell easily)
        // Lower demand → higher penalty (outlet bears the full loss)
        double penalty = Math.round(BASE_PENALTY * (1 - avgDemandScore) * 100.0) / 100.0;

        // STEP 5: Apply to student
        User student = order.getStudent();
        int newNoShows = student.getNoShowCount() + 1;

        student.setNoShowCount(newNoShows);
        student.setPendingPenaltyAmount(student.getPendingPenaltyAmount() + penalty);

        // STEP 6: Escalate account status after 3 no-shows
        if (newNoShows >= 3) {
            student.setAccountStatus("WARNING");
        }

        userRepository.save(student);

        // Notify the student about the penalty — critical for trust & transparency
        String statusMsg = newNoShows >= 3
                ? " Your account has been flagged (WARNING status). You must clear penalties before placing new orders."
                : " Total no-shows: " + newNoShows + "/3 before account warning.";

        notificationRepository.save(new Notification(
                student,
                "Penalty Applied — ₹" + String.format("%.2f", penalty),
                "You did not collect your order #" + order.getId() + " from "
                        + order.getOutlet().getName() + ". A no-show penalty of ₹"
                        + String.format("%.2f", penalty) + " has been charged to your account."
                        + statusMsg + " Pay penalties from the Penalties section.",
                Notification.TYPE_PENALTY_APPLIED));

        log.info(
                "[PenaltyService] Order #{} no-show | student={} | demandScore={} | penalty=₹{} | no-shows={}",
                order.getId(), student.getEmail(), String.format("%.2f", avgDemandScore),
                String.format("%.2f", penalty), newNoShows);
    }

    /**
     * Get demand score for a menu item at a given time.
     * Tries the ML service first (if enabled); falls back to rule-based.
     */
    private double getDemandScore(Long menuItemId, LocalDateTime expiresAt) {

        if (!mlClient.isHealthy()) {
            return calculateRuleBasedScore(menuItemId, expiresAt);
        }

        return mlClient.predictDemandScore(menuItemId, expiresAt);
    }

    // ── Rule-based demand score ────────────────────────────────────────────────

    private double calculateRuleBasedScore(Long menuItemId, LocalDateTime expiresAt) {

        int expiredMinutes = expiresAt.getHour() * 60 + expiresAt.getMinute();
        int windowStart = Math.max(0, expiredMinutes - WINDOW_MINUTES);
        int windowEnd = Math.min(1439, expiredMinutes + WINDOW_MINUTES);

        LocalDateTime since = expiresAt.minusDays(LOOKBACK_DAYS);

        long itemDemand = orderRepository.countDemandInWindow(
                menuItemId, windowStart, windowEnd, since);

        List<Long> maxList = orderRepository.getMaxDemandInWindow(
                windowStart, windowEnd, since);

        if (maxList.isEmpty() || maxList.get(0) == 0) {
            return 0.5; // cold-start default
        }

        double score = (double) itemDemand / maxList.get(0);
        return Math.max(0.1, Math.min(0.9, score));
    }
}