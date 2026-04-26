package com.smartcampus.backend.controller;
 
import com.smartcampus.backend.domain.Order;
import com.smartcampus.backend.domain.Outlet;
import com.smartcampus.backend.domain.User;
import com.smartcampus.backend.dto.CounterOrderRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.OrderRepository;
import com.smartcampus.backend.repository.OutletRepository;
import com.smartcampus.backend.repository.UserRepository;
import com.smartcampus.backend.service.OrderService;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Manager-specific endpoints:
 *
 * POST /api/manager/orders/counter — place a counter/walk-in order (billing)
 * GET /api/manager/orders/ledger — today's full ledger (all orders, all
 * sources)
 * GET /api/manager/orders/ledger/summary — today's sales summary (totals,
 * counts)
 *
 * All endpoints require MANAGER role and resolve the manager's outlet
 * automatically
 * from their JWT — a manager can only see/bill for their own outlet.
 */
@RestController
@RequestMapping("/api/manager")
public class ManagerOrderController {

    private final OrderService orderService;
    private final OrderRepository orderRepository;
    private final OutletRepository outletRepository;
    private final UserRepository userRepository;

    public ManagerOrderController(OrderService orderService,
            OrderRepository orderRepository,
            OutletRepository outletRepository,
            UserRepository userRepository) {
        this.orderService = orderService;
        this.orderRepository = orderRepository;
        this.outletRepository = outletRepository;
        this.userRepository = userRepository;
    }

    // ── 1. Place a counter / walk-in order ───────────────────────────────────

    /**
     * Manager creates a billing entry for a walk-in customer (parent, visitor,
     * etc.)
     * or a registered student who didn't use the app.
     *
     * The order is immediately PICKED + PAID — no OTP flow, no slot countdown.
     * Optionally, manager can link it to a slot to track capacity.
     *
     * POST /api/manager/orders/counter
     * Role: MANAGER
     */
    @PostMapping("/orders/counter")
    public Map<String, Object> placeCounterOrder(
            @RequestBody CounterOrderRequest request,
            Authentication auth) {

        String email = (String) auth.getPrincipal();
        User manager = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("Manager not found", 404));

        // Find manager's outlet
        var outlet = outletRepository.findByManagerId(manager.getId())
                .orElseThrow(() -> new ApiException("No outlet found for this manager", 404));

        Order order = orderService.createCounterOrder(
                outlet.getId(),
                manager.getId(),
                request.getCustomerName(),
                request.getPaymentMode() != null ? request.getPaymentMode() : "CASH",
                request.getSlotId(),
                request.getItems());

        // Build a receipt-style response
        Map<String, Object> receipt = new HashMap<>();
        receipt.put("orderId", order.getId());
        receipt.put("customerName", order.getCustomerName());
        receipt.put("totalAmount", order.getTotalAmount());
        receipt.put("paymentMode", order.getPaymentMode());
        receipt.put("status", order.getStatus());
        receipt.put("orderSource", order.getOrderSource());
        receipt.put("createdAt", order.getCreatedAt());
        receipt.put("message", "Counter order billed successfully. Amount: ₹" +
                String.format("%.2f", order.getTotalAmount()));
        return receipt;
    }

    // ── 2. Today's full ledger ────────────────────────────────────────────────

    /**
     * Returns ALL orders for the manager's outlet today (midnight to now).
     * Includes both PLATFORM orders (student app) and COUNTER orders (walk-ins).
     * Manager uses this like a daily register / cash book.
     *
     * GET /api/manager/orders/ledger
     * GET /api/manager/orders/ledger?date=2024-12-15 (historical day)
     * Role: MANAGER
     */
    @GetMapping("/orders/ledger")
    public Map<String, Object> getDailyLedger(
            @RequestParam(required = false) String date,
            Authentication auth) {

        String email = (String) auth.getPrincipal();
        User manager = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("Manager not found", 404));

        var outlet = outletRepository.findByManagerId(manager.getId())
                .orElseThrow(() -> new ApiException("No outlet found for this manager", 404));

        LocalDate targetDate = (date != null) ? LocalDate.parse(date) : LocalDate.now();
        LocalDateTime dayStart = targetDate.atStartOfDay();
        LocalDateTime dayEnd = targetDate.atTime(LocalTime.MAX);

        List<Order> allOrders = orderRepository
                .findByOutletIdAndCreatedAtBetweenOrderByCreatedAtDesc(
                        outlet.getId(), dayStart, dayEnd);

        // Enrich each order into a ledger entry
        List<Map<String, Object>> entries = allOrders.stream().map(o -> {
            Map<String, Object> entry = new HashMap<>();
            entry.put("orderId", o.getId());
            entry.put("orderSource", o.getOrderSource());
            entry.put("customerName", o.getOrderSource().equals("COUNTER")
                    ? o.getCustomerName()
                    : (o.getStudent() != null ? o.getStudent().getFullName() : "Unknown"));
            entry.put("totalAmount", o.getTotalAmount());
            entry.put("paymentMode", o.getPaymentMode());
            entry.put("paymentStatus", o.getPaymentStatus());
            entry.put("status", o.getStatus());
            entry.put("createdAt", o.getCreatedAt());
            return entry;
        }).collect(Collectors.toList());

        Map<String, Object> ledger = new HashMap<>();
        ledger.put("outletId", outlet.getId());
        ledger.put("outletName", outlet.getName());
        ledger.put("date", targetDate.toString());
        ledger.put("orders", entries);
        ledger.put("totalOrders", allOrders.size());
        return ledger;
    }

    // ── 3. Today's sales summary (the dashboard stat cards) ──────────────────

    /**
     * Returns aggregated sales numbers for today. This is what the manager sees
     * at the top of their dashboard — like a quick P&L for the day.
     *
     * GET /api/manager/orders/ledger/summary
     * GET /api/manager/orders/ledger/summary?date=2024-12-15
     * Role: MANAGER
     */
    @GetMapping("/orders/ledger/summary")
    public Map<String, Object> getDailySummary(
            @RequestParam(required = false) String date,
            Authentication auth) {

        String email = (String) auth.getPrincipal();
        User manager = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("Manager not found", 404));

        var outlet = outletRepository.findByManagerId(manager.getId())
                .orElseThrow(() -> new ApiException("No outlet found for this manager", 404));

        LocalDate targetDate = (date != null) ? LocalDate.parse(date) : LocalDate.now();
        LocalDateTime dayStart = targetDate.atStartOfDay();
        LocalDateTime dayEnd = targetDate.atTime(LocalTime.MAX);

        List<Order> allOrders = orderRepository
                .findByOutletIdAndCreatedAtBetweenOrderByCreatedAtDesc(
                        outlet.getId(), dayStart, dayEnd);

        // ── Compute summary stats ─────────────────────────────────────────────

        long totalOrders = allOrders.size();

        // Revenue breakdown
        double totalRevenue = allOrders.stream()
                .filter(o -> "PAID".equals(o.getPaymentStatus()))
                .mapToDouble(Order::getTotalAmount).sum();

        double cashRevenue = allOrders.stream()
                .filter(o -> "PAID".equals(o.getPaymentStatus()) && "CASH".equals(o.getPaymentMode()))
                .mapToDouble(Order::getTotalAmount).sum();

        double onlineRevenue = allOrders.stream()
                .filter(o -> "PAID".equals(o.getPaymentStatus()) && "ONLINE".equals(o.getPaymentMode()))
                .mapToDouble(Order::getTotalAmount).sum();

        // Order source breakdown
        long platformOrders = allOrders.stream()
                .filter(o -> "PLATFORM".equals(o.getOrderSource())).count();

        long counterOrders = allOrders.stream()
                .filter(o -> "COUNTER".equals(o.getOrderSource())).count();

        // Status breakdown
        long completedOrders = allOrders.stream()
                .filter(o -> "PICKED".equals(o.getStatus())).count();

        long cancelledOrders = allOrders.stream()
                .filter(o -> "CANCELLED".equals(o.getStatus())).count();

        long activeOrders = allOrders.stream()
                .filter(o -> List.of("PLACED", "PREPARING", "READY").contains(o.getStatus())).count();

        long pendingPayment = allOrders.stream()
                .filter(o -> "PENDING".equals(o.getPaymentStatus())).count();

        // Average order value (completed only)
        double avgOrderValue = completedOrders > 0 ? totalRevenue / completedOrders : 0.0;

        Map<String, Object> summary = new HashMap<>();
        summary.put("date", targetDate.toString());
        summary.put("outletName", outlet.getName());
        summary.put("totalOrders", totalOrders);
        summary.put("completedOrders", completedOrders);
        summary.put("cancelledOrders", cancelledOrders);
        summary.put("activeOrders", activeOrders);
        summary.put("pendingPayment", pendingPayment);
        summary.put("platformOrders", platformOrders);
        summary.put("counterOrders", counterOrders);
        summary.put("totalRevenue", Math.round(totalRevenue * 100.0) / 100.0);
        summary.put("cashRevenue", Math.round(cashRevenue * 100.0) / 100.0);
        summary.put("onlineRevenue", Math.round(onlineRevenue * 100.0) / 100.0);
        summary.put("avgOrderValue", Math.round(avgOrderValue * 100.0) / 100.0);

        return summary;
    }
}