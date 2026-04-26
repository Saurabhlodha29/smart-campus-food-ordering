package com.smartcampus.backend.service;

import com.smartcampus.backend.domain.*;
import com.smartcampus.backend.dto.OrderItemRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.*;
import com.smartcampus.backend.service.SseEmitterRegistry;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Random;

@Service
public class OrderService {

        private final OrderRepository orderRepository;
        private final UserRepository userRepository;
        private final OutletRepository outletRepository;
        private final PickupSlotRepository slotRepository;
        private final MenuItemRepository menuItemRepository;
        private final OrderItemRepository orderItemRepository;
        private final NotificationRepository notificationRepository;
        private final MLClient mlClient;
        private final SseEmitterRegistry sseEmitterRegistry;

        private static final double LOAD_FACTOR = 0.5;
        private static final int GRACE_MINUTES = 30;
        private static final Random RANDOM = new Random();

        public OrderService(OrderRepository orderRepository,
                        UserRepository userRepository,
                        OutletRepository outletRepository,
                        PickupSlotRepository slotRepository,
                        MenuItemRepository menuItemRepository,
                        OrderItemRepository orderItemRepository,
                        NotificationRepository notificationRepository,
                        MLClient mlClient,
                        SseEmitterRegistry sseEmitterRegistry) {
                this.orderRepository = orderRepository;
                this.userRepository = userRepository;
                this.outletRepository = outletRepository;
                this.slotRepository = slotRepository;
                this.menuItemRepository = menuItemRepository;
                this.orderItemRepository = orderItemRepository;
                this.notificationRepository = notificationRepository;
                this.mlClient = mlClient;
                this.sseEmitterRegistry = sseEmitterRegistry;
        }

        @Transactional
        public Order createOrder(Long studentId,
                        Long outletId,
                        Long slotId,
                        String paymentMode,
                        List<OrderItemRequest> items) {

                if (items == null || items.isEmpty()) {
                        throw new ApiException("Order must have at least one item", 400);
                }

                User student = userRepository.findById(studentId)
                                .orElseThrow(() -> new ApiException("Student not found", 404));

                // Block students with unpaid penalties
                if ("WARNING".equals(student.getAccountStatus())
                                && student.getPendingPenaltyAmount() > 0) {
                        throw new ApiException(
                                        "Your account has unpaid penalties of ₹"
                                                        + String.format("%.2f", student.getPendingPenaltyAmount())
                                                        + ". Please clear them before placing a new order.",
                                        403);
                }

                Outlet outlet = outletRepository.findById(outletId)
                                .orElseThrow(() -> new ApiException("Outlet not found", 404));

		if (!Outlet.STATUS_ACTIVE.equals(outlet.getStatus())) {
			String reason = Outlet.STATUS_CLOSED.equals(outlet.getStatus())
					? "This outlet is currently closed. Please check back later."
					: "This outlet is not currently accepting orders.";
			throw new ApiException(reason, 400);
		}

		// Daily order limit per outlet — prevents abuse and slot monopolisation
		long todayOrderCount = orderRepository.countOrdersPlacedTodayByStudentAtOutlet(studentId, outletId);
		if (todayOrderCount >= 3) {
			throw new ApiException(
					"You have already placed " + todayOrderCount + " orders at this outlet today. "
					+ "The daily limit is 3 orders per outlet.",
					400);
		}

		if (!outlet.isWithinOperatingHours()) {
			String openStr = outlet.getOpeningTime() != null ? outlet.getOpeningTime().toString() : "N/A";
			String closeStr = outlet.getClosingTime() != null ? outlet.getClosingTime().toString() : "N/A";
			throw new ApiException(
					"This outlet is not accepting orders right now. Operating hours: "
							+ openStr + " – " + closeStr,
					400);
		}

		PickupSlot slot = slotRepository.findById(slotId)
                                .orElseThrow(() -> new ApiException("Slot not found", 404));

                if (slot.getCurrentOrders() >= slot.getMaxOrders()) {
                        throw new ApiException("This pickup slot is full. Please choose another slot.", 400);
                }

                // Validate items and calculate total
                double totalAmount = 0;
                for (OrderItemRequest itemRequest : items) {
                        MenuItem menuItem = menuItemRepository.findById(itemRequest.getMenuItemId())
                                        .orElseThrow(() -> new ApiException(
                                                        "Menu item not found: " + itemRequest.getMenuItemId(), 404));
                        if (!menuItem.isAvailable()) {
                                throw new ApiException("'" + menuItem.getName() + "' is currently unavailable.", 400);
                        }
                        if (itemRequest.getQuantity() <= 0) {
                                throw new ApiException("Quantity must be at least 1 for item: " + menuItem.getName(),
                                                400);
                        }
                        totalAmount += menuItem.getPrice() * itemRequest.getQuantity();
                }

                // ML wait time prediction: dynamic estimate based on kitchen load
                int activeCount = orderRepository.findByPickupSlotAndStatusNot(slot, "PICKED").size();
                int waitMinutes = mlClient.predictWaitTime(outletId, items.size(), activeCount);
                LocalDateTime readyAt = LocalDateTime.now().plusMinutes(waitMinutes);
                LocalDateTime expiresAt = readyAt.plusMinutes(GRACE_MINUTES);

                Order order = new Order(
                                student, outlet, slot,
                                "PLACED",
                                totalAmount,
                                paymentMode,
                                "PENDING",
                                readyAt,
                                expiresAt);
                order.setOrderSource("PLATFORM");

                // COD orders get OTP immediately; ONLINE orders get OTP after payment verified
                if ("COD".equals(paymentMode)) {
                        order.setPickupOtp(generateOtp());
                }

                orderRepository.save(order);

                // ML no-show risk: flag high-risk students (requires PLATFORM source)
                double noShowRisk = mlClient.predictNoShowRisk(studentId, totalAmount, slot.getStartTime().getHour());
                if (noShowRisk >= 0.65) {
                        notificationRepository.save(new Notification(
                                        outlet.getManager(),
                                        "High Risk Order",
                                        "Order #" + order.getId() + " has a high no-show risk ("
                                                        + String.format("%.0f%%", noShowRisk * 100)
                                                        + "). Consider calling the student.",
                                        Notification.TYPE_ORDER_STATUS_CHANGED));
                }

                // Save order items
                for (OrderItemRequest itemRequest : items) {
                        MenuItem menuItem = menuItemRepository.findById(itemRequest.getMenuItemId()).get();
                        orderItemRepository.save(new OrderItem(
                                        order, menuItem, itemRequest.getQuantity(), menuItem.getPrice()));
                }

                // Increment slot load
                slot.incrementCurrentOrders();
                slotRepository.save(slot);

	return order;
	}

	/**
	 * Re-orders items from a past order.
	 * Copies items from the original order into a fresh new order.
	 * Student must supply a new slotId and paymentMode.
	 * Items that are no longer available are silently skipped (not an error — UX
	 * matches Swiggy).
	 * If ALL items are unavailable, throws 400.
	 */
	@Transactional
	public Order repeatOrder(Long originalOrderId, Long studentId, Long slotId, String paymentMode) {

		Order original = orderRepository.findById(originalOrderId)
				.orElseThrow(() -> new ApiException("Original order not found", 404));

		if (original.getStudent() == null || !original.getStudent().getId().equals(studentId)) {
			throw new ApiException("You can only repeat your own orders.", 403);
		}

		List<OrderItem> originalItems = orderItemRepository.findByOrderId(originalOrderId);
		if (originalItems.isEmpty()) {
			throw new ApiException("Original order has no items to repeat.", 400);
		}

		// Build new item requests — skip unavailable items
		List<OrderItemRequest> newItems = originalItems.stream()
				.filter(oi -> oi.getMenuItem().isAvailable())
				.map(oi -> {
					OrderItemRequest r = new OrderItemRequest();
					r.setMenuItemId(oi.getMenuItem().getId());
					r.setQuantity(oi.getQuantity());
					return r;
				})
				.collect(java.util.stream.Collectors.toList());

		if (newItems.isEmpty()) {
			throw new ApiException(
					"None of the items from your original order are currently available.", 400);
		}

		return createOrder(studentId, original.getOutlet().getId(), slotId, paymentMode, newItems);
	}

        /**
         * Student cancels their own order.
         * Rules:
         * - Can only cancel PLACED orders (not yet accepted by manager)
         * - ONLINE + not yet PAID orders can be cancelled freely (no charge)
         * - ONLINE + PAID orders: cancellation triggers a refund flag (manual refund
         * process)
         * - COD orders: cancel immediately (no charge as food not yet prepared)
         * - Decrements slot count so the slot opens up for others
         */
        @Transactional
        public Order cancelOrder(Long orderId, Long requestingStudentId) {

                Order order = orderRepository.findById(orderId)
                                .orElseThrow(() -> new ApiException("Order not found", 404));

                // Ownership check — students can only cancel their own orders
                if (order.getStudent() == null || !order.getStudent().getId().equals(requestingStudentId)) {
                        throw new ApiException("You can only cancel your own orders.", 403);
                }

                String currentStatus = order.getStatus();

                if ("PICKED".equals(currentStatus) || "EXPIRED".equals(currentStatus)
                                || "CANCELLED".equals(currentStatus)) {
                        throw new ApiException(
                                        "This order cannot be cancelled. Current status: " + currentStatus, 400);
                }

                if ("PREPARING".equals(currentStatus) || "READY".equals(currentStatus)) {
                        throw new ApiException(
                                        "Cannot cancel — the outlet has already started preparing your order. "
                                                        + "Please contact the outlet directly.",
                                        400);
                }

                // Only PLACED orders can be cancelled by the student
                order.setStatus("CANCELLED");

                // If paid online, flag for refund
                if ("ONLINE".equals(order.getPaymentMode()) && "PAID".equals(order.getPaymentStatus())) {
                        order.setPaymentStatus("REFUND_PENDING");
                }

                orderRepository.save(order);
                sseEmitterRegistry.pushStatusUpdate(orderId, "CANCELLED");

                // Release the slot capacity so another student can book it
                PickupSlot slot = order.getPickupSlot();
                slot.decrementCurrentOrders();
                slotRepository.save(slot);

                // Notify the outlet manager of the cancellation
                Outlet outlet = order.getOutlet();
                notificationRepository.save(new Notification(
                                outlet.getManager(),
                                "Order Cancelled",
                                "Order #" + orderId + " by " + order.getStudent().getFullName()
                                                + " has been cancelled (₹"
                                                + String.format("%.2f", order.getTotalAmount()) + ").",
                                Notification.TYPE_ORDER_STATUS_CHANGED));

                return order;
        }

        /**
         * Manager submits the student's 4-digit OTP to confirm pickup.
         * For ONLINE orders: must already be paymentStatus=PAID.
         * For CASH orders: confirms cash received AND marks pickup simultaneously.
         */
        @Transactional
        public Order confirmPickup(Long orderId, String submittedOtp) {

                Order order = orderRepository.findById(orderId)
                                .orElseThrow(() -> new ApiException("Order not found", 404));

                if (!"READY".equals(order.getStatus())) {
                        throw new ApiException(
                                        "Order cannot be picked up — current status is: " + order.getStatus()
                                                        + ". Order must be READY first.",
                                        400);
                }

                if ("ONLINE".equals(order.getPaymentMode())
                                && !"PAID".equals(order.getPaymentStatus())) {
                        throw new ApiException(
                                        "Online payment has not been completed for this order.", 400);
                }

                if (order.getPickupOtp() == null) {
                        throw new ApiException("No OTP found for this order.", 500);
                }

                if (!order.getPickupOtp().equals(submittedOtp)) {
                        throw new ApiException("Incorrect OTP. Please ask the student to show their OTP again.", 400);
                }

                order.setStatus("PICKED");

                if ("COD".equals(order.getPaymentMode())) {
                        order.setPaymentStatus("PAID");
                }

                orderRepository.save(order);
                sseEmitterRegistry.pushStatusUpdate(orderId, "PICKED");

                // Notify the student their order was picked up
                if (order.getStudent() != null) {
                        notificationRepository.save(new Notification(
                                        order.getStudent(),
                                        "Order Picked Up",
                                        "Your order #" + orderId + " from " + order.getOutlet().getName()
                                                        + " has been marked as picked up. Enjoy your meal!",
                                        Notification.TYPE_ORDER_STATUS_CHANGED));
                }

                return order;
        }

        /**
         * Manager places an order at the counter for a walk-in customer.
         * - No student account needed (works for parents, visitors, etc.)
         * - No slot required (but manager CAN optionally link to a slot to track
         * capacity)
         * - Payment is marked PAID immediately (cash collected on spot, or UPI
         * reference taken)
         * - Slot currentOrders is incremented only if slotId is provided
         * - Order is created in PICKED status directly (food given immediately at
         * counter)
         * OR in PLACED/PREPARING flow if manager wants to track prep (optional flag)
         */
        @Transactional
        public Order createCounterOrder(Long outletId,
                        Long managerId,
                        String customerName,
                        String paymentMode,
                        Long slotId,
                        List<OrderItemRequest> items) {

                if (items == null || items.isEmpty()) {
                        throw new ApiException("Order must have at least one item", 400);
                }

                Outlet outlet = outletRepository.findById(outletId)
                                .orElseThrow(() -> new ApiException("Outlet not found", 404));

                // Validate items and calculate total
                double totalAmount = 0;
                for (OrderItemRequest itemRequest : items) {
                        MenuItem menuItem = menuItemRepository.findById(itemRequest.getMenuItemId())
                                        .orElseThrow(() -> new ApiException(
                                                        "Menu item not found: " + itemRequest.getMenuItemId(), 404));
                        if (!menuItem.isAvailable()) {
                                throw new ApiException("'" + menuItem.getName() + "' is currently unavailable.", 400);
                        }
                        if (itemRequest.getQuantity() <= 0) {
                                throw new ApiException("Quantity must be at least 1 for: " + menuItem.getName(), 400);
                        }
                        totalAmount += menuItem.getPrice() * itemRequest.getQuantity();
                }

                // Counter orders: no student, no predicted wait time, immediate
                LocalDateTime now = LocalDateTime.now();
                Order order = new Order(
                                null, // no student
                                outlet,
                                null, // no slot (set below if provided)
                                "PICKED", // immediately picked — customer is standing there
                                totalAmount,
                                paymentMode,
                                "PAID", // cash/UPI collected immediately
                                now, // readyAt = now
                                now.plusMinutes(30) // expiresAt irrelevant but required by schema
                );
                order.setOrderSource("COUNTER");
                order.setCustomerName(customerName != null ? customerName : "Walk-in Customer");
                order.setPickupOtp(null); // no OTP needed — customer is at counter

                // If manager specifies a slot (e.g., for capacity tracking), link it
                if (slotId != null) {
                        PickupSlot slot = slotRepository.findById(slotId)
                                        .orElseThrow(() -> new ApiException("Slot not found", 404));
                        // Don't block on capacity for counter orders — manager decision
                        order.setPickupSlot(slot);
                        // Still increment so the slot count reflects actual load
                        if (!slot.isFull()) {
                                slot.incrementCurrentOrders();
                        } else {
                                // Manager is manually overriding — just add 1 without throwing
                                slot.setCurrentOrdersManually(slot.getCurrentOrders() + 1);
                        }
                        slotRepository.save(slot);
                }

                orderRepository.save(order);

                // Save order items
                for (OrderItemRequest itemRequest : items) {
                        MenuItem menuItem = menuItemRepository.findById(itemRequest.getMenuItemId()).get();
                        orderItemRepository.save(
                                        new OrderItem(order, menuItem, itemRequest.getQuantity(), menuItem.getPrice()));
                }

                return order;
        }

        @Transactional
        public Order updateOrderStatus(Long orderId, String newStatus) {

                Order order = orderRepository.findById(orderId)
                                .orElseThrow(() -> new ApiException("Order not found", 404));

                String currentStatus = order.getStatus();
                if (!isValidTransition(currentStatus, newStatus)) {
                        throw new ApiException(
                                        "Invalid status transition: " + currentStatus + " → " + newStatus
                                                        + ". Allowed: PLACED→PREPARING, PREPARING→READY",
                                        400);
                }

                order.setStatus(newStatus);
                orderRepository.save(order);
                sseEmitterRegistry.pushStatusUpdate(orderId, newStatus);

                // Notify the student of the status change
                String message = switch (newStatus) {
                        case "PREPARING" -> "Your order #" + orderId + " from " + order.getOutlet().getName()
                                        + " is now being prepared! Estimated ready time: "
                                        + order.getReadyAt().toLocalTime().toString();
                        case "READY" -> "🎉 Your order #" + orderId + " from " + order.getOutlet().getName()
                                        + " is READY for pickup! Show your OTP to the manager. "
                                        + "Please collect within 30 minutes to avoid a penalty.";
                        default -> "Your order #" + orderId + " status has been updated to: " + newStatus;
                };

                if (order.getStudent() != null) {
                        notificationRepository.save(new Notification(
                                        order.getStudent(),
                                        "Order Update — " + newStatus,
                                        message,
                                        Notification.TYPE_ORDER_STATUS_CHANGED));
                }

                return order;
        }

        // ── Helpers ───────────────────────────────────────────────────────────────

        public static String generateOtp() {
                return String.format("%04d", RANDOM.nextInt(10000));
        }

        private boolean isValidTransition(String current, String next) {
                return switch (current) {
                        case "PLACED" -> "PREPARING".equals(next);
                        case "PREPARING" -> "READY".equals(next);
                        default -> false;
                };
        }
}