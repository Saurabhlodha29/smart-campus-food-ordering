package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.OutletApplication;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface OutletApplicationRepository extends JpaRepository<OutletApplication, Long> {

    /** All applications from this manager email (to count attempts). */
    List<OutletApplication> findByManagerEmail(String email);

    /** Count total submissions by this manager email. */
    long countByManagerEmail(String email);

    /** Pending applications for a specific campus — shown on Admin dashboard. */
    List<OutletApplication> findByCampusIdAndStatusOrderByCreatedAtDesc(Long campusId, String status);

    /** All applications for a campus (any status). */
    List<OutletApplication> findByCampusIdOrderByCreatedAtDesc(Long campusId);

    /** All pending applications (SuperAdmin view). */
    List<OutletApplication> findByStatusOrderByCreatedAtDesc(String status);
}