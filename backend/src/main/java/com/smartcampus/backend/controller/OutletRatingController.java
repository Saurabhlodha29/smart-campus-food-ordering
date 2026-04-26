package com.smartcampus.backend.controller;

import com.smartcampus.backend.domain.*;
import com.smartcampus.backend.dto.OutletRatingRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.*;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Outlet rating endpoints.
 *
 * POST /api/ratings/order/{orderId}  — student submits rating after pickup
 * GET  /api/ratings/outlet/{outletId}/summary — average rating + count (public)
 */
@RestController
@RequestMapping("/api/ratings")
public class OutletRatingController {

    private final OutletRatingRepository ratingRepository;
    private final OrderRepository orderRepository;
    private final OutletRepository outletRepository;
    private final UserRepository userRepository;

    public OutletRatingController(OutletRatingRepository ratingRepository,
                                   OrderRepository orderRepository,
                                   OutletRepository outletRepository,
                                   UserRepository userRepository) {
        this.ratingRepository = ratingRepository;
        this.orderRepository = orderRepository;
        this.outletRepository = outletRepository;
        this.userRepository = userRepository;
    }

    /**
     * Student submits a 1–5 star rating for the outlet, tied to a specific order.
     * Rules:
     * - Order must be in PICKED status (only completed orders can be rated)
     * - Student must be the owner of the order
     * - Each order can only be rated once (unique constraint on order_id)
     */
    @PostMapping("/order/{orderId}")
    public Map<String, Object> rateOutlet(
            @PathVariable Long orderId,
            @RequestBody OutletRatingRequest request,
            Authentication auth) {

        String email = (String) auth.getPrincipal();
        User student = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", 404));

        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new ApiException("Order not found", 404));

        if (order.getStudent() == null || !order.getStudent().getId().equals(student.getId())) {
            throw new ApiException("You can only rate your own orders.", 403);
        }
        if (!"PICKED".equals(order.getStatus())) {
            throw new ApiException("You can only rate an order after it has been picked up.", 400);
        }
        if (ratingRepository.existsByOrderId(orderId)) {
            throw new ApiException("You have already rated this order.", 400);
        }
        if (request.getStars() < 1 || request.getStars() > 5) {
            throw new ApiException("Stars must be between 1 and 5.", 400);
        }

        OutletRating rating = new OutletRating(
                order.getOutlet(), student, order, request.getStars(), request.getComment());
        ratingRepository.save(rating);

        double newAvg = ratingRepository.getAverageRatingForOutlet(order.getOutlet().getId());
        long count    = ratingRepository.getRatingCountForOutlet(order.getOutlet().getId());

        return Map.of(
                "message", "Rating submitted. Thank you!",
                "outletId", order.getOutlet().getId(),
                "outletAverageRating", Math.round(newAvg * 10.0) / 10.0,
                "totalRatings", count);
    }

    /**
     * Returns the average rating and count for an outlet.
     * Used by Flutter to display star rating on the outlet card.
     * GET /api/ratings/outlet/{outletId}/summary
     */
    @GetMapping("/outlet/{outletId}/summary")
    public Map<String, Object> getOutletRatingSummary(@PathVariable Long outletId) {
        outletRepository.findById(outletId)
                .orElseThrow(() -> new ApiException("Outlet not found", 404));

        double avg = ratingRepository.getAverageRatingForOutlet(outletId);
        long count = ratingRepository.getRatingCountForOutlet(outletId);

        return Map.of(
                "outletId", outletId,
                "averageRating", Math.round(avg * 10.0) / 10.0,
                "totalRatings", count);
    }
}
