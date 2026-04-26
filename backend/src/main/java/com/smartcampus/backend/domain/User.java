package com.smartcampus.backend.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties({ "hibernateLazyInitializer", "handler" })

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 120)
    private String fullName;

    @Column(nullable = false, unique = true, length = 150)
    private String email;

    @JsonIgnore
    @Column(nullable = false)
    private String passwordHash;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "role_id", nullable = false)
    private Role role;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "campus_id")
    private Campus campus;

    @Column(nullable = false)
    private boolean isActive = true;

    @Column(nullable = false)
    private int noShowCount = 0;

    @Column(nullable = false)
    private double pendingPenaltyAmount = 0.0;

    @Column(nullable = false, length = 30)
    private String accountStatus = "ACTIVE";

    @Column(length = 15)
    private String phone;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @Column(length = 300)
    private String fcmToken;

    protected User() {
        // JPA only
    }

    public User(String fullName, String email, String passwordHash, Role role, Campus campus) {
        this.fullName = fullName;
        this.email = email;
        this.passwordHash = passwordHash;
        this.role = role;
        this.campus = campus;
        this.createdAt = LocalDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public String getFullName() {
        return fullName;
    }

    public String getEmail() {
        return email;
    }

    public String getPasswordHash() {
        return passwordHash;
    }

    public Role getRole() {
        return role;
    }

    public Campus getCampus() {
        return campus;
    }

    public boolean isActive() {
        return isActive;
    }

    public int getNoShowCount() {
        return noShowCount;
    }

    public double getPendingPenaltyAmount() {
        return pendingPenaltyAmount;
    }

    public String getAccountStatus() {
        return accountStatus;
    }

    public String getPhone() {
        return phone;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public String getFcmToken() {
        return fcmToken;
    }

    public void setNoShowCount(int noShowCount) {
        this.noShowCount = noShowCount;
    }

    public void setPendingPenaltyAmount(double pendingPenaltyAmount) {
        this.pendingPenaltyAmount = pendingPenaltyAmount;
    }

    public void setAccountStatus(String accountStatus) {
        this.accountStatus = accountStatus;
    }

    public void setPasswordHash(String passwordHash) {
        this.passwordHash = passwordHash;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }

    public void setFcmToken(String token) {
        this.fcmToken = token;
    }
}