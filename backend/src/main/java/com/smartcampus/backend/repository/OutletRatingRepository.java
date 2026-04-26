package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.OutletRating;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface OutletRatingRepository extends JpaRepository<OutletRating, Long> {

    boolean existsByOrderId(Long orderId);

    Optional<OutletRating> findByOrderId(Long orderId);

    @Query("SELECT COALESCE(AVG(r.stars), 0.0) FROM OutletRating r WHERE r.outlet.id = :outletId")
    double getAverageRatingForOutlet(@Param("outletId") Long outletId);

    @Query("SELECT COUNT(r) FROM OutletRating r WHERE r.outlet.id = :outletId")
    long getRatingCountForOutlet(@Param("outletId") Long outletId);
}
