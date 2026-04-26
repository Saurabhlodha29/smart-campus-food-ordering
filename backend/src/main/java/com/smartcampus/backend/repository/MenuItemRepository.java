package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.MenuItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface MenuItemRepository extends JpaRepository<MenuItem, Long> {

    /** All items for an outlet (manager view — includes out-of-stock). */
    List<MenuItem> findByOutletId(Long outletId);

    /** Available items only — shown to students on the ordering screen. */
    List<MenuItem> findByOutletIdAndIsAvailableTrue(Long outletId);

    /** Search globally across all available items */
    List<MenuItem> findByNameContainingIgnoreCaseAndIsAvailableTrue(String query);

    @Query("SELECT m FROM MenuItem m WHERE LOWER(m.name) LIKE LOWER(CONCAT('%', :q, '%')) AND m.isAvailable = true")
    List<MenuItem> searchByName(@Param("q") String q);
}