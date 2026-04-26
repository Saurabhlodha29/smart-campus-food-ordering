package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.PickupSlot;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import jakarta.persistence.LockModeType;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface PickupSlotRepository extends JpaRepository<PickupSlot, Long> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    Optional<PickupSlot> findById(Long id);

    // ── Date-filtered queries (fix for "old slots accumulate forever") ────────

    /**
     * Slots for a specific outlet on a specific date.
     * Used by the student ordering screen: call with outletId + today.
     */
    List<PickupSlot> findByOutletIdAndSlotDate(Long outletId, LocalDate slotDate);

    /**
     * All slots for a specific outlet from a given date onward (inclusive).
     * Used by the manager dashboard: they need to see today + upcoming slots.
     */
    List<PickupSlot> findByOutletIdAndSlotDateGreaterThanEqualOrderBySlotDateAscStartTimeAsc(
            Long outletId, LocalDate fromDate);

    /**
     * All slots on a specific date across all outlets.
     * Used as a fallback when no outletId is supplied.
     */
    List<PickupSlot> findBySlotDate(LocalDate slotDate);

    // ── Cleanup ───────────────────────────────────────────────────────────────

    /**
     * Bulk-delete all slots whose date is strictly before the given cutoff.
     * Called nightly at midnight to purge yesterday's (and older) slots.
     * Returns the count of deleted rows for logging.
     */
    @Modifying
    @Query("DELETE FROM PickupSlot ps WHERE ps.slotDate < :cutoff")
    int deleteBySlotDateBefore(@Param("cutoff") LocalDate cutoff);
}