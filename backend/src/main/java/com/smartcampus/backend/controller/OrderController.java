package com.smartcampus.backend.controller;

import com.smartcampus.backend.domain.Order;
import com.smartcampus.backend.domain.User;
import com.smartcampus.backend.dto.OtpRequest;
import com.smartcampus.backend.dto.OrderRequest;
import com.smartcampus.backend.dto.RepeatOrderRequest;
import com.smartcampus.backend.dto.OrderStatusRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.OrderRepository;
import com.smartcampus.backend.repository.UserRepository;
import com.smartcampus.backend.repository.OrderItemRepository;
import com.smartcampus.backend.dto.OrderDetailResponse;
import com.smartcampus.backend.dto.OrderItemResponse;
import com.smartcampus.backend.service.OrderService;
import com.smartcampus.backend.service.SseEmitterRegistry;
import java.util.stream.Collectors;
import jakarta.validation.Valid;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Map;

/**
 * Order endpoints.
 *
 * POST /api/orders STUDENT — place a new order
 * GET /api/orders/student/{studentId} STUDENT — all orders for a student
 * GET /api/orders/{id} Authenticated — single order detail
 * GET /api/orders ADMIN/SUPERADMIN — all orders (platform-wide)
 * GET /api/orders/outlet/{outletId} MANAGER — all orders for their outlet
 * PATCH /api/orders/{id}/status MANAGER — advance status
 * (PLACED→PREPARING→READY)
 * POST /api/orders/{id}/pickup MANAGER — submit OTP to confirm pickup
 * POST /api/orders/{id}/cancel STUDENT — cancel a PLACED order
 */
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final OrderService orderService;
    private final OrderRepository orderRepository;
    private final UserRepository userRepository;
    private final OrderItemRepository orderItemRepository;
    private final SseEmitterRegistry sseEmitterRegistry;

    public OrderController(OrderService orderService,
            OrderRepository orderRepository,
            UserRepository userRepository,
            OrderItemRepository orderItemRepository,
            SseEmitterRegistry sseEmitterRegistry) {
        this.orderService = orderService;
        this.orderRepository = orderRepository;
        this.userRepository = userRepository;
        this.orderItemRepository = orderItemRepository;
        this.sseEmitterRegistry = sseEmitterRegistry;
    }

    // ── Platform-wide (Admin / SuperAdmin) ───────────────────────────────────

    /** All orders on the platform — Admin/SuperAdmin dashboard only. */
    @GetMapping
    public List<Order> getAllOrders() {
        return orderRepository.findAll();
    }

    // ── Single order ─────────────────────────────────────────────────────────

    @GetMapping("/{id}")
    public OrderDetailResponse getOrderById(@PathVariable Long id) {
        Order order = orderRepository.findById(id)
                .orElseThrow(() -> new ApiException("Order not found", 404));

        List<OrderItemResponse> itemResponses = orderItemRepository.findByOrderId(id)
                .stream()
                .map(oi -> new OrderItemResponse(
                        oi.getMenuItem().getId(),
                        oi.getMenuItem().getName(),
                        oi.getMenuItem().getPhotoUrl(),
                        oi.getQuantity(),
                        oi.getPriceAtOrder()))
                .collect(Collectors.toList());

        return new OrderDetailResponse(order, itemResponses);
    }

    /**
     * SSE stream for real-time order status updates.
     * GET /api/orders/{id}/events
     * Flutter calls this once after placing/loading an order.
     * The server pushes {"orderId": 5, "status": "PREPARING"} events as they happen.
     * Connection closes automatically when order reaches terminal state
     * (PICKED/CANCELLED/EXPIRED).
     */
    @GetMapping(value = "/{id}/events", produces = "text/event-stream")
    public SseEmitter streamOrderEvents(@PathVariable Long id) {
        // Validate order exists
        orderRepository.findById(id)
                .orElseThrow(() -> new ApiException("Order not found", 404));
        return sseEmitterRegistry.createEmitter(id);
    }

    // ── Student: their own order history (newest first) ──────────────────────

    @GetMapping("/student/{studentId}")
    public List<OrderDetailResponse> getOrdersByStudent(@PathVariable Long studentId) {
        return orderRepository.findByStudentIdOrderByCreatedAtDesc(studentId)
                .stream()
                .map(order -> {
                    List<OrderItemResponse> items = orderItemRepository.findByOrderId(order.getId())
                            .stream()
                            .map(oi -> new OrderItemResponse(
                                    oi.getMenuItem().getId(),
                                    oi.getMenuItem().getName(),
                                    oi.getMenuItem().getPhotoUrl(),
                                    oi.getQuantity(),
                                    oi.getPriceAtOrder()))
                            .collect(Collectors.toList());
                    return new OrderDetailResponse(order, items);
                })
                .collect(Collectors.toList());
    }

    // ── Manager: orders for their outlet ─────────────────────────────────────

    /**
     * Returns orders for a given outlet, newest first.
     * Optional ?status=PLACED,PREPARING,READY filter so the Flutter manager
     * dashboard can load only live (active) orders without fetching everything.
     *
     * Examples:
     * GET /api/orders/outlet/3 — all orders
     * GET /api/orders/outlet/3?status=PLACED — only PLACED
     * GET /api/orders/outlet/3?status=PLACED,PREPARING,READY — live tab
     */
    @GetMapping("/outlet/{outletId}")
    public List<Order> getOrdersByOutlet(
            @PathVariable Long outletId,
            @RequestParam(required = false) String status) {

        if (status != null && !status.isBlank()) {
            // Single status filter
            return orderRepository.findByOutletIdAndStatusOrderByCreatedAtDesc(outletId, status);
        }
        return orderRepository.findByOutletIdOrderByCreatedAtDesc(outletId);
    }

    // ── Student: place a new order ────────────────────────────────────────────

    @PostMapping
    public Order createOrder(@RequestBody OrderRequest request) {
        return orderService.createOrder(
                request.getStudentId(),
                request.getOutletId(),
                request.getSlotId(),
                request.getPaymentMode(),
                request.getItems());
    }

    /**
     * Repeat a past order. Copies items from originalOrderId into a new order.
     * POST /api/orders/repeat/{orderId}
     * Body: { "studentId": 1, "slotId": 3, "paymentMode": "COD" }
     */
    @PostMapping("/repeat/{orderId}")
    public Order repeatOrder(
            @PathVariable Long orderId,
            @RequestBody RepeatOrderRequest request) {
        return orderService.repeatOrder(orderId, request.getStudentId(),
                request.getSlotId(), request.getPaymentMode());
    }

    // ── Student: cancel a PLACED order ───────────────────────────────────────

    /**
     * Cancels a PLACED order. Only works before the manager starts preparing.
     * The student's slot capacity is released so other students can book it.
     *
     * For ONLINE + PAID orders: paymentStatus is set to REFUND_PENDING.
     * Refunds are processed manually by the admin (until automated refund API is
     * added).
     *
     * POST /api/orders/{id}/cancel
     * Role: STUDENT (authenticated — studentId resolved from JWT)
     *
     * Response: { "message": "...", "orderId": 5, "status": "CANCELLED" }
     */
    @PostMapping("/{id}/cancel")
    public Map<String, Object> cancelOrder(@PathVariable Long id,
            Authentication auth) {
        String email = (String) auth.getPrincipal();
        User student = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", 404));

        Order order = orderService.cancelOrder(id, student.getId());

        return Map.of(
                "message", "Order cancelled successfully.",
                "orderId", order.getId(),
                "status", order.getStatus(),
                "paymentStatus", order.getPaymentStatus());
    }

    // ── Manager: advance order status ────────────────────────────────────────

    /**
     * Advance order status: PLACED → PREPARING → READY.
     * The final step (READY → PICKED) is done exclusively via POST /{id}/pickup
     * with OTP.
     * Student is automatically notified on each status change.
     */
    @PatchMapping("/{id}/status")
    public Order updateStatus(@PathVariable Long id,
            @RequestBody OrderStatusRequest request) {
        return orderService.updateOrderStatus(id, request.getStatus());
    }

    // ── Manager: confirm pickup via OTP ──────────────────────────────────────

    /**
     * Manager confirms student pickup by verifying the 4-digit OTP.
     * For ONLINE: order must already be paymentStatus=PAID.
     * For COD: cash is assumed collected at this moment — paymentStatus set to
     * PAID.
     */
    @PostMapping("/{id}/pickup")
    public Map<String, Object> confirmPickup(
            @PathVariable Long id,
            @Valid @RequestBody OtpRequest request) {

        Order order = orderService.confirmPickup(id, request.getOtp());

        return Map.of(
                "message", "Order picked up successfully.",
                "orderId", order.getId(),
                "status", order.getStatus(),
                "paymentStatus", order.getPaymentStatus());
    }
}