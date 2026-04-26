package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.Outlet;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface OutletRepository extends JpaRepository<Outlet, Long> {

    /** All outlets for a campus (any status) — used by campus admin. */
    List<Outlet> findByCampusId(Long campusId);

    /** Outlets with a specific status for a campus — e.g. ACTIVE only for students. */
    List<Outlet> findByCampusIdAndStatus(Long campusId, String status);

    /**
     * Outlets with any of the given statuses for a campus.
     * Used for the student "visible" endpoint: returns ACTIVE + CLOSED so the
     * Flutter UI can show closed outlets greyed out.
     */
    List<Outlet> findByCampusIdAndStatusIn(Long campusId, List<String> statuses);

    /** Find all outlets managed by a specific user. */
    Optional<Outlet> findByManagerId(Long managerId);

    /** All outlets with a given status across the platform — single status. */
    List<Outlet> findByStatus(String status);

    /**
     * All outlets whose status is in the given list — used by the payout scheduler
     * to process ACTIVE + CLOSED outlets in a single query.
     */
    List<Outlet> findByStatusIn(List<String> statuses);
}