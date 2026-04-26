package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.OutletPayout;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface OutletPayoutRepository extends JpaRepository<OutletPayout, Long> {

    List<OutletPayout> findByOutletIdOrderByCreatedAtDesc(Long outletId);

    List<OutletPayout> findAllByOrderByCreatedAtDesc();

    Optional<OutletPayout> findByRazorpayPayoutId(String razorpayPayoutId);

    /** Prevent duplicate payouts for the same outlet and same period. */
    boolean existsByOutletIdAndPeriodStart(Long outletId, LocalDate periodStart);

    @Query("SELECT op FROM OutletPayout op WHERE op.status = 'FAILED' ORDER BY op.createdAt DESC")
    List<OutletPayout> findFailedPayouts();

    /** Sum the net amount already paid to an outlet — for accounting. */
    @Query("SELECT COALESCE(SUM(op.netAmount), 0) FROM OutletPayout op " +
           "WHERE op.outlet.id = :outletId AND op.status IN ('SIMULATED','PAID')")
    double sumPaidNetAmount(@Param("outletId") Long outletId);

    /**
     * All payout records for outlets belonging to a specific campus.
     * Used by the campus ADMIN endpoint to view payout history for their campus.
     */
    @Query("SELECT op FROM OutletPayout op " +
           "WHERE op.outlet.campus.id = :campusId " +
           "ORDER BY op.createdAt DESC")
    List<OutletPayout> findByCampusIdOrderByCreatedAtDesc(@Param("campusId") Long campusId);
}