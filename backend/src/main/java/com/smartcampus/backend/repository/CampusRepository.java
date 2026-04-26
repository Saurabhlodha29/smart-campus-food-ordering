package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.Campus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface CampusRepository extends JpaRepository<Campus, Long> {

    /** Used to auto-assign campus to student during self-registration. */
    Optional<Campus> findByEmailDomain(String emailDomain);

    boolean existsByEmailDomain(String emailDomain);
}