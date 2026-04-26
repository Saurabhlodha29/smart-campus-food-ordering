package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.AdminApplication;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface AdminApplicationRepository extends JpaRepository<AdminApplication, Long> {

    /** All applications from this email (to count previous attempts). */
    List<AdminApplication> findByApplicantEmail(String email);

    /** Count total submissions by this email (across all statuses). */
    long countByApplicantEmail(String email);

    /** Pending applications — shown on the SuperAdmin dashboard. */
    List<AdminApplication> findByStatusOrderByCreatedAtDesc(String status);

    /** All applications for a given campus email domain. */
    List<AdminApplication> findByCampusEmailDomain(String domain);

    /**
     * Check whether a campus with this email domain already has an approved
     * admin application (prevents duplicate campus registrations).
     */
    boolean existsByCampusEmailDomainAndStatus(String domain, String status);
}