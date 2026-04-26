package com.smartcampus.backend.controller;

import com.smartcampus.backend.domain.Outlet;
import com.smartcampus.backend.domain.PickupSlot;
import com.smartcampus.backend.dto.PickupSlotRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.OutletRepository;
import com.smartcampus.backend.repository.PickupSlotRepository;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import com.smartcampus.backend.service.PickupSlotService;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/**
 * Pickup slot management.
 *
 * GET  /api/slots?outletId=X              — today's slots for an outlet (students / ordering)
 * GET  /api/slots/upcoming?outletId=X    — today + future slots (manager view)
 * POST /api/slots                         — create a slot (MANAGER only)
 * DELETE /api/slots/{id}                  — delete a specific slot (MANAGER only)
 *
 * Security is declared in SecurityConfig:
 *   GET  /api/slots/**  → authenticated
 *   POST /api/slots     → MANAGER
 *   DELETE /api/slots/* → MANAGER
 *
 * The nightly slot cleanup (past slots auto-delete) is in PickupSlotService.
 */
@RestController
@RequestMapping("/api/slots")
public class PickupSlotController {

    private final PickupSlotRepository slotRepository;
    private final OutletRepository     outletRepository;

    public PickupSlotController(PickupSlotRepository slotRepository,
                                OutletRepository outletRepository) {
        this.slotRepository  = slotRepository;
        this.outletRepository = outletRepository;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // GET /api/slots?outletId=X
    // Returns TODAY's slots only for the given outlet.
    // If no outletId is provided, returns all slots for today (fallback).
    // ─────────────────────────────────────────────────────────────────────────

    @GetMapping
    public List<PickupSlot> getTodaySlots(
            @RequestParam(required = false) Long outletId) {

        LocalDate today = LocalDate.now();

        if (outletId != null) {
            return slotRepository.findByOutletIdAndSlotDate(outletId, today);
        }

        // No filter — return all of today's slots (useful for debugging/admin)
        return slotRepository.findBySlotDate(today);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // GET /api/slots/upcoming?outletId=X
    // Returns today's + future slots for a given outlet.
    // Managers use this to review and manage their upcoming schedule.
    // ─────────────────────────────────────────────────────────────────────────

    @GetMapping("/upcoming")
    public List<PickupSlot> getUpcomingSlots(
            @RequestParam(required = false) Long outletId) {

        LocalDate today = LocalDate.now();

        if (outletId != null) {
            return slotRepository
                    .findByOutletIdAndSlotDateGreaterThanEqualOrderBySlotDateAscStartTimeAsc(
                            outletId, today);
        }

        // Fallback: all upcoming slots across all outlets (SuperAdmin use case)
        return slotRepository.findAll().stream()
                .filter(s -> !s.getSlotDate().isBefore(today))
                .toList();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // POST /api/slots — Create a slot (MANAGER only)
    // ─────────────────────────────────────────────────────────────────────────

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public PickupSlot createSlot(@RequestBody PickupSlotRequest request) {

        Outlet outlet = outletRepository.findById(request.getOutletId())
                .orElseThrow(() -> new ApiException("Outlet not found", 404));

        if (request.getStartTime() == null || request.getEndTime() == null) {
            throw new ApiException("startTime and endTime are required", 400);
        }
        if (!request.getEndTime().isAfter(request.getStartTime())) {
            throw new ApiException("endTime must be after startTime", 400);
        }
        if (request.getMaxOrders() < 1) {
            throw new ApiException("maxOrders must be at least 1", 400);
        }

        PickupSlot slot = new PickupSlot(
                outlet,
                request.getStartTime(),
                request.getEndTime(),
                request.getMaxOrders()
        );

        return slotRepository.save(slot);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // DELETE /api/slots/{id} — Delete a specific slot (MANAGER only)
    // ─────────────────────────────────────────────────────────────────────────

    @DeleteMapping("/{id}")
    public Map<String, String> deleteSlot(@PathVariable Long id) {

        PickupSlot slot = slotRepository.findById(id)
                .orElseThrow(() -> new ApiException("Slot not found", 404));

        if (slot.getCurrentOrders() > 0) {
            throw new ApiException(
                "Cannot delete a slot that already has " + slot.getCurrentOrders()
                + " order(s) assigned to it.", 400);
        }

        slotRepository.delete(slot);
        return Map.of("message", "Slot deleted", "slotId", String.valueOf(id));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PATCH /api/slots/{id}/adjust-count
    // Manager manually adjusts the currentOrders count on a slot.
    // Use case: retroactively account for off-platform orders, corrections, etc.
    // Body: { "adjustment": 3 }   → adds 3 to currentOrders
    // Body: { "adjustment": -1 }  → removes 1 from currentOrders
    // ─────────────────────────────────────────────────────────────────────────

    @PatchMapping("/{id}/adjust-count")
    public Map<String, Object> adjustSlotCount(
            @PathVariable Long id,
            @RequestBody Map<String, Integer> body) {

        PickupSlot slot = slotRepository.findById(id)
                .orElseThrow(() -> new ApiException("Slot not found", 404));

        Integer adjustment = body.get("adjustment");
        if (adjustment == null) {
            throw new ApiException("'adjustment' field is required", 400);
        }

        int newCount = slot.getCurrentOrders() + adjustment;
        if (newCount < 0) {
            throw new ApiException("Cannot reduce count below 0. Current: " + slot.getCurrentOrders(), 400);
        }

        slot.setCurrentOrdersManually(newCount);
        slotRepository.save(slot);

        return Map.of(
            "message", "Slot count adjusted",
            "slotId", id,
            "previousCount", slot.getCurrentOrders() - adjustment,
            "newCount", newCount,
            "maxOrders", slot.getMaxOrders()
        );
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PATCH /api/slots/{id}/capacity
    // Manager updates the maximum capacity of a slot (they could already do this
    // by deleting and recreating — this is a cleaner in-place update).
    // Body: { "maxOrders": 30 }
    // ─────────────────────────────────────────────────────────────────────────

    @PatchMapping("/{id}/capacity")
    public PickupSlot updateSlotCapacity(
            @PathVariable Long id,
            @RequestBody Map<String, Integer> body) {

        PickupSlot slot = slotRepository.findById(id)
                .orElseThrow(() -> new ApiException("Slot not found", 404));

        Integer maxOrders = body.get("maxOrders");
        if (maxOrders == null || maxOrders < 1) {
            throw new ApiException("'maxOrders' must be at least 1", 400);
        }
        if (maxOrders < slot.getCurrentOrders()) {
            throw new ApiException("Cannot set maxOrders (" + maxOrders +
                ") below current order count (" + slot.getCurrentOrders() + ")", 400);
        }

        slot.setMaxOrders(maxOrders);
        slotRepository.save(slot);
        return slot;
    }
}