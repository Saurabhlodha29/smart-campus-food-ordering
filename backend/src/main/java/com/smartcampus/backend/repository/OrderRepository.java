package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.Order;
import com.smartcampus.backend.domain.PickupSlot;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface OrderRepository extends JpaRepository<Order, Long> {

    List<Order> findByPickupSlotAndStatusNot(PickupSlot slot, String status);

    /** Used by PenaltyService to find genuine no-shows: READY but past expiry. */
    List<Order> findByStatusAndExpiresAtBefore(String status, LocalDateTime now);

    /**
     * Used by PenaltyService to find orders that expired without being prepared.
     * Status is one of [PLACED, PREPARING] — no penalty is charged for these.
     */
    List<Order> findByStatusInAndExpiresAtBefore(List<String> statuses, LocalDateTime now);

    /** All orders for a student, newest first (student order history screen). */
    List<Order> findByStudentIdOrderByCreatedAtDesc(Long studentId);

    /** @deprecated Use findByStudentIdOrderByCreatedAtDesc for proper ordering. */
    @Deprecated
    List<Order> findByStudentId(Long studentId);

    /**
     * Manager: filter orders for an outlet by status — avoids returning thousands
     * of rows to Flutter.
     */
    List<Order> findByOutletIdAndStatusOrderByCreatedAtDesc(Long outletId, String status);

    /**
     * All orders for a specific outlet — used by the manager dashboard.
     * Returns orders in descending creation order (newest first).
     */
    List<Order> findByOutletIdOrderByCreatedAtDesc(Long outletId);

    /**
     * All orders for an outlet within a time range (used for ledger/summary endpoints).
     */
    List<Order> findByOutletIdAndCreatedAtBetweenOrderByCreatedAtDesc(
            Long outletId, LocalDateTime from, LocalDateTime to);

    // ── ML demand queries ─────────────────────────────────────────────────────

    @Query(value = """
                SELECT COUNT(oi.id) FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE oi.menu_item_id = :menuItemId
                AND (EXTRACT(HOUR FROM o.created_at) * 60 + EXTRACT(MINUTE FROM o.created_at))
                    BETWEEN :windowStartMinutes AND :windowEndMinutes
                AND o.created_at >= :since
                AND o.status != 'CANCELLED'
            """, nativeQuery = true)
    long countDemandInWindow(
            @Param("menuItemId") Long menuItemId,
            @Param("windowStartMinutes") int windowStartMinutes,
            @Param("windowEndMinutes") int windowEndMinutes,
            @Param("since") LocalDateTime since);

    @Query(value = """
                SELECT COUNT(oi.id) FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE (EXTRACT(HOUR FROM o.created_at) * 60 + EXTRACT(MINUTE FROM o.created_at))
                    BETWEEN :windowStartMinutes AND :windowEndMinutes
                AND o.created_at >= :since
                AND o.status != 'CANCELLED'
                GROUP BY oi.menu_item_id
                ORDER BY COUNT(oi.id) DESC
            """, nativeQuery = true)
    List<Long> getMaxDemandInWindow(
            @Param("windowStartMinutes") int windowStartMinutes,
            @Param("windowEndMinutes") int windowEndMinutes,
            @Param("since") LocalDateTime since);

    // ── Payout queries — ONLINE orders ────────────────────────────────────────

    /**
     * Sum of order totals for PICKED + ONLINE + PAID orders within a date range.
     * This is the gross amount the platform collected via Razorpay for this outlet.
     * The platform transfers netAmount (gross − commission) to the outlet's bank.
     */
    @Query(value = """
                SELECT COALESCE(SUM(o.total_amount), 0.0)
                FROM orders o
                WHERE o.outlet_id = :outletId
                  AND o.status           = 'PICKED'
                  AND o.payment_mode     = 'ONLINE'
                  AND o.payment_status   = 'PAID'
                  AND o.created_at BETWEEN :from AND :to
            """, nativeQuery = true)
    double sumOnlinePaidPickedAmountForOutlet(
            @Param("outletId") Long outletId,
            @Param("from") LocalDateTime from,
            @Param("to") LocalDateTime to);

    @Query(value = """
                SELECT COUNT(o.id)
                FROM orders o
                WHERE o.outlet_id = :outletId
                  AND o.status           = 'PICKED'
                  AND o.payment_mode     = 'ONLINE'
                  AND o.payment_status   = 'PAID'
                  AND o.created_at BETWEEN :from AND :to
            """, nativeQuery = true)
    long countOnlinePaidPickedOrdersForOutlet(
            @Param("outletId") Long outletId,
            @Param("from") LocalDateTime from,
            @Param("to") LocalDateTime to);

    // ── Payout queries — CASH (COD) orders ───────────────────────────────────

    /**
     * Sum of order totals for PICKED + CASH + PAID orders within a date range.
     * This money was collected directly by the manager in cash — the platform
     * does NOT transfer this. Tracked here for reporting/transparency only.
     */
    @Query(value = """
                SELECT COALESCE(SUM(o.total_amount), 0.0)
                FROM orders o
                WHERE o.outlet_id = :outletId
                  AND o.status           = 'PICKED'
                  AND o.payment_mode     = 'CASH'
                  AND o.payment_status   = 'PAID'
                  AND o.created_at BETWEEN :from AND :to
            """, nativeQuery = true)
    double sumCashPaidPickedAmountForOutlet(
            @Param("outletId") Long outletId,
            @Param("from") LocalDateTime from,
            @Param("to") LocalDateTime to);

    @Query(value = """
                SELECT COUNT(o.id)
                FROM orders o
                WHERE o.outlet_id = :outletId
                  AND o.status           = 'PICKED'
                  AND o.payment_mode     = 'CASH'
                  AND o.payment_status   = 'PAID'
                  AND o.created_at BETWEEN :from AND :to
            """, nativeQuery = true)
    long countCashPaidPickedOrdersForOutlet(
            @Param("outletId") Long outletId,
            @Param("from") LocalDateTime from,
            @Param("to") LocalDateTime to);

    @Query(value = """
            SELECT
                DATE(o.created_at) AS order_date,
                COUNT(o.id) AS order_count,
                COALESCE(SUM(o.total_amount), 0) AS revenue
            FROM orders o
            WHERE o.outlet_id = :outletId
              AND o.status = 'PICKED'
              AND o.created_at >= :since
            GROUP BY DATE(o.created_at)
            ORDER BY DATE(o.created_at) ASC
            """, nativeQuery = true)
    List<Object[]> getDailyRevenueForOutlet(
            @Param("outletId") Long outletId,
            @Param("since") LocalDateTime since);

    @Query(value = """
            SELECT COUNT(o.id) FROM orders o
            WHERE o.student_id = :studentId
              AND o.outlet_id = :outletId
              AND DATE(o.created_at) = CURRENT_DATE
              AND o.status NOT IN ('CANCELLED', 'EXPIRED')
            """, nativeQuery = true)
    long countOrdersPlacedTodayByStudentAtOutlet(
            @Param("studentId") Long studentId,
            @Param("outletId") Long outletId);
}