package com.smartcampus.backend.service;

import com.smartcampus.backend.repository.PickupSlotRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;

/**
 * Handles automatic cleanup of pickup slots that belong to past dates.
 *
 * <h3>Why this is needed</h3>
 * Slots have no expiry logic — without a date field they were stored forever and
 * the GET /api/slots endpoint returned stale slots from previous days.
 * The fix is two-part:
 * <ol>
 *   <li>The {@code slotDate} field added to {@link com.smartcampus.backend.domain.PickupSlot}
 *       lets the controller filter by today's date.</li>
 *   <li>This scheduler runs at midnight every day and bulk-deletes slots for
 *       any date before today, keeping the table clean.</li>
 * </ol>
 *
 * <h3>Safety</h3>
 * Only slots with {@code slotDate < today} are deleted — today's and future slots
 * are never touched. Slots that have active orders ({@code currentOrders > 0})
 * are deleted too because by the time the scheduler runs (midnight), those orders
 * are already in a terminal state (PICKED, EXPIRED, etc.) and the slot record
 * serves no further operational purpose.
 */
@Service
public class PickupSlotService {

    private static final Logger log = LoggerFactory.getLogger(PickupSlotService.class);

    private final PickupSlotRepository slotRepository;

    public PickupSlotService(PickupSlotRepository slotRepository) {
        this.slotRepository = slotRepository;
    }

    /**
     * Runs every day at 00:05 AM (5 minutes after midnight so day rollover is clean).
     * Deletes all pickup slots whose {@code slotDate} is strictly before today.
     */
    @Scheduled(cron = "0 5 0 * * *")
    @Transactional
    public void cleanupPastSlots() {
        LocalDate today = LocalDate.now();
        int deleted = slotRepository.deleteBySlotDateBefore(today);
        if (deleted > 0) {
            log.info("[SlotCleanup] Deleted {} past slot(s) older than {}.", deleted, today);
        } else {
            log.debug("[SlotCleanup] No past slots to clean up for {}.", today);
        }
    }
}