package com.smartcampus.backend.domain;

import jakarta.persistence.*;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.time.LocalDateTime;

/**
 * In-app notifications delivered to users.
 *
 * Triggered by:
 * - Admin application approved/rejected (→ Campus Admin)
 * - Outlet application approved/rejected (→ Outlet Manager)
 * - Order status change (→ Student) [future]
 */
@JsonIgnoreProperties({ "hibernateLazyInitializer", "handler" })
@Entity
@Table(name = "notifications")
public class Notification {

    // ── Type constants ────────────────────────────────────────────────────────
    public static final String TYPE_ADMIN_APP_APPROVED = "ADMIN_APP_APPROVED";
    public static final String TYPE_ADMIN_APP_REJECTED = "ADMIN_APP_REJECTED";
    public static final String TYPE_OUTLET_APP_APPROVED = "OUTLET_APP_APPROVED";
    public static final String TYPE_OUTLET_APP_REJECTED = "OUTLET_APP_REJECTED";
    public static final String TYPE_ORDER_STATUS_CHANGED = "ORDER_STATUS_CHANGED";
    public static final String TYPE_PENALTY_APPLIED = "PENALTY_APPLIED";
    public static final String TYPE_ORDER_CANCELLED = "ORDER_CANCELLED";
    public static final String TYPE_VERIFICATION_DONE = "VERIFICATION_DONE";

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** The user who receives this notification. */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String message;

    @Column(nullable = false, length = 50)
    private String type;

    @Column(nullable = false)
    private boolean isRead = false;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    protected Notification() {
    }

    public Notification(User user, String title, String message, String type) {
        this.user = user;
        this.title = title;
        this.message = message;
        this.type = type;
        this.createdAt = LocalDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public User getUser() {
        return user;
    }

    public String getTitle() {
        return title;
    }

    public String getMessage() {
        return message;
    }

    public String getType() {
        return type;
    }

    public boolean isRead() {
        return isRead;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void markRead() {
        this.isRead = true;
    }
}