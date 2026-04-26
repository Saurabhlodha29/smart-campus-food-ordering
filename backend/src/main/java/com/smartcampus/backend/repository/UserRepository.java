package com.smartcampus.backend.repository;

import com.smartcampus.backend.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);

    /** All users on a campus — used by admin dashboard user management. */
    List<User> findByCampusId(Long campusId);
}