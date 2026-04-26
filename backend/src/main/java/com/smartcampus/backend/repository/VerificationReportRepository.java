package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.VerificationReport;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface VerificationReportRepository extends JpaRepository<VerificationReport, Long> {

    /** Fetch the verification report for a specific outlet application. */
    Optional<VerificationReport> findByOutletApplicationId(Long outletApplicationId);
}