package com.smartcampus.backend.domain;

import jakarta.persistence.*;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.time.LocalDateTime;

/**
 * Represents an outlet manager's application to register their outlet
 * on a specific campus.
 *
 * Status flow: PENDING → APPROVED | REJECTED
 * Re-apply: Max 3 total attempts tracked by managerEmail.
 * On APPROVED, the Outlet + Manager User are auto-created.
 * The outlet starts in PENDING_LAUNCH state — the manager
 * must add menu items and click "Launch" to go live.
 *
 * Document fields (FSSAI, GSTIN, PAN, Bank) are submitted by the manager
 * and automatically verified by DocumentVerificationService right after
 * the application is saved. Results are stored in the linked
 * VerificationReport.
 */
@JsonIgnoreProperties({ "hibernateLazyInitializer", "handler" })
@Entity
@Table(name = "outlet_applications")
public class OutletApplication {

    public static final String STATUS_PENDING = "PENDING";
    public static final String STATUS_APPROVED = "APPROVED";
    public static final String STATUS_REJECTED = "REJECTED";

    public static final int MAX_ATTEMPTS = 3;

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // ── Manager / applicant info ──────────────────────────────────────────────
    @Column(nullable = false, length = 120)
    private String managerName;

    @Column(nullable = false, length = 150)
    private String managerEmail;

    // ── Outlet info ───────────────────────────────────────────────────────────
    @Column(nullable = false, length = 150)
    private String outletName;

    @Column(columnDefinition = "TEXT")
    private String outletDescription;

    @Column(nullable = false)
    private int avgPrepTime;

    @Column(nullable = false, length = 500)
    private String licenseDocUrl;

    @Column(length = 500)
    private String outletPhotoUrl;

    // ── Document verification fields ──────────────────────────────────────────
    @Column(length = 20)
    private String fssaiLicenseNumber;

    @Column(length = 20)
    private String gstin;

    @Column(length = 15)
    private String panNumber;

    @Column(length = 25)
    private String bankAccountNumber;

    @Column(length = 15)
    private String bankIfscCode;

    // ── Campus ────────────────────────────────────────────────────────────────
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "campus_id", nullable = false)
    private Campus campus;

    // ── Review tracking ───────────────────────────────────────────────────────
    @Column(nullable = false, length = 20)
    private String status = STATUS_PENDING;

    @Column(columnDefinition = "TEXT")
    private String rejectionReason;

    @Column(nullable = false)
    private int attemptNumber = 1;

    @Column
    private LocalDateTime reviewedAt;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_outlet_id")
    private Outlet createdOutlet;

    @OneToOne(mappedBy = "outletApplication", fetch = FetchType.LAZY, cascade = CascadeType.ALL, orphanRemoval = true)
    private VerificationReport verificationReport;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    protected OutletApplication() {
    }

    /** Original constructor — no document fields (kept for safety). */
    public OutletApplication(String managerName, String managerEmail,
            String outletName, String outletDescription,
            int avgPrepTime, String licenseDocUrl,
            String outletPhotoUrl, Campus campus, int attemptNumber) {
        this.managerName = managerName;
        this.managerEmail = managerEmail;
        this.outletName = outletName;
        this.outletDescription = outletDescription;
        this.avgPrepTime = avgPrepTime;
        this.licenseDocUrl = licenseDocUrl;
        this.outletPhotoUrl = outletPhotoUrl;
        this.campus = campus;
        this.attemptNumber = attemptNumber;
        this.createdAt = LocalDateTime.now();
    }

    /** Full constructor including document verification fields. */
    public OutletApplication(String managerName, String managerEmail,
            String outletName, String outletDescription,
            int avgPrepTime, String licenseDocUrl,
            String outletPhotoUrl, Campus campus, int attemptNumber,
            String fssaiLicenseNumber, String gstin,
            String panNumber, String bankAccountNumber,
            String bankIfscCode) {
        this(managerName, managerEmail, outletName, outletDescription,
                avgPrepTime, licenseDocUrl, outletPhotoUrl, campus, attemptNumber);
        this.fssaiLicenseNumber = fssaiLicenseNumber != null ? fssaiLicenseNumber.trim() : null;
        this.gstin = gstin != null ? gstin.trim().toUpperCase() : null;
        this.panNumber = panNumber != null ? panNumber.trim().toUpperCase() : null;
        this.bankAccountNumber = bankAccountNumber != null ? bankAccountNumber.trim() : null;
        this.bankIfscCode = bankIfscCode != null ? bankIfscCode.trim().toUpperCase() : null;
    }

    // ── Getters ───────────────────────────────────────────────────────────────
    public Long getId() {
        return id;
    }

    public String getManagerName() {
        return managerName;
    }

    public String getManagerEmail() {
        return managerEmail;
    }

    public String getOutletName() {
        return outletName;
    }

    public String getOutletDescription() {
        return outletDescription;
    }

    public int getAvgPrepTime() {
        return avgPrepTime;
    }

    public String getLicenseDocUrl() {
        return licenseDocUrl;
    }

    public String getOutletPhotoUrl() {
        return outletPhotoUrl;
    }

    public String getFssaiLicenseNumber() {
        return fssaiLicenseNumber;
    }

    public String getGstin() {
        return gstin;
    }

    public String getPanNumber() {
        return panNumber;
    }

    public String getBankAccountNumber() {
        return bankAccountNumber;
    }

    public String getBankIfscCode() {
        return bankIfscCode;
    }

    public Campus getCampus() {
        return campus;
    }

    public String getStatus() {
        return status;
    }

    public String getRejectionReason() {
        return rejectionReason;
    }

    public int getAttemptNumber() {
        return attemptNumber;
    }

    public LocalDateTime getReviewedAt() {
        return reviewedAt;
    }

    public Outlet getCreatedOutlet() {
        return createdOutlet;
    }

    public VerificationReport getVerificationReport() {
        return verificationReport;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    // ── State transitions ─────────────────────────────────────────────────────
    public void approve(Outlet outlet) {
        this.status = STATUS_APPROVED;
        this.createdOutlet = outlet;
        this.reviewedAt = LocalDateTime.now();
    }

    public void reject(String reason) {
        this.status = STATUS_REJECTED;
        this.rejectionReason = reason;
        this.reviewedAt = LocalDateTime.now();
    }
}