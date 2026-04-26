package com.smartcampus.backend.domain;

import jakarta.persistence.*;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.time.LocalDateTime;

/**
 * Represents a person's application to become the Campus Admin
 * for a new campus on the Smart Campus platform.
 *
 * Status flow:  PENDING → APPROVED | REJECTED
 * Re-apply:     Max 3 total attempts tracked by applicantEmail.
 *               On APPROVED, the Campus + Admin User are auto-created.
 */
@JsonIgnoreProperties({"hibernateLazyInitializer", "handler"})
@Entity
@Table(name = "admin_applications")
public class AdminApplication {

    // ── Status constants ──────────────────────────────────────────────────────
    public static final String STATUS_PENDING  = "PENDING";
    public static final String STATUS_APPROVED = "APPROVED";
    public static final String STATUS_REJECTED = "REJECTED";

    public static final int MAX_ATTEMPTS = 3;

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // ── Applicant info ────────────────────────────────────────────────────────
    @Column(nullable = false, length = 120)
    private String fullName;

    /** Must use the official campus email domain they are claiming. */
    @Column(nullable = false, length = 150)
    private String applicantEmail;

    /**
     * Free-text field: their post/designation at the campus
     * (e.g. "Student Council Mess Secretary", "College Administrative Officer").
     */
    @Column(nullable = false, columnDefinition = "TEXT")
    private String designation;

    /** URL of uploaded campus ID card photo (client uploads to cloud, sends URL). */
    @Column(nullable = false, length = 500)
    private String idCardPhotoUrl;

    // ── Campus info being claimed ─────────────────────────────────────────────
    @Column(nullable = false, length = 150)
    private String campusName;

    @Column(nullable = false, length = 200)
    private String campusLocation;

    /**
     * The official email domain of the campus (e.g. "bennett.edu.in").
     * SuperAdmin verifies this is a real, legitimate institutional domain.
     */
    @Column(nullable = false, length = 100)
    private String campusEmailDomain;

    // ── Review tracking ───────────────────────────────────────────────────────
    @Column(nullable = false, length = 20)
    private String status = STATUS_PENDING;

    @Column(columnDefinition = "TEXT")
    private String rejectionReason;

    @Column(nullable = false)
    private int attemptNumber = 1;   // increments on each re-application (max 3)

    @Column
    private LocalDateTime reviewedAt;

    // ── Reference to created campus (set on approval) ─────────────────────────
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_campus_id")
    private Campus createdCampus;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    protected AdminApplication() {}

    public AdminApplication(String fullName,
                             String applicantEmail,
                             String designation,
                             String idCardPhotoUrl,
                             String campusName,
                             String campusLocation,
                             String campusEmailDomain,
                             int    attemptNumber) {
        this.fullName          = fullName;
        this.applicantEmail    = applicantEmail;
        this.designation       = designation;
        this.idCardPhotoUrl    = idCardPhotoUrl;
        this.campusName        = campusName;
        this.campusLocation    = campusLocation;
        this.campusEmailDomain = campusEmailDomain;
        this.attemptNumber     = attemptNumber;
        this.createdAt         = LocalDateTime.now();
    }

    // ── Getters ───────────────────────────────────────────────────────────────
    public Long getId()                  { return id; }
    public String getFullName()          { return fullName; }
    public String getApplicantEmail()    { return applicantEmail; }
    public String getDesignation()       { return designation; }
    public String getIdCardPhotoUrl()    { return idCardPhotoUrl; }
    public String getCampusName()        { return campusName; }
    public String getCampusLocation()    { return campusLocation; }
    public String getCampusEmailDomain() { return campusEmailDomain; }
    public String getStatus()            { return status; }
    public String getRejectionReason()   { return rejectionReason; }
    public int    getAttemptNumber()     { return attemptNumber; }
    public LocalDateTime getReviewedAt() { return reviewedAt; }
    public Campus getCreatedCampus()     { return createdCampus; }
    public LocalDateTime getCreatedAt()  { return createdAt; }

    // ── Setters ───────────────────────────────────────────────────────────────
    public void approve(Campus campus) {
        this.status        = STATUS_APPROVED;
        this.createdCampus = campus;
        this.reviewedAt    = LocalDateTime.now();
    }

    public void reject(String reason) {
        this.status          = STATUS_REJECTED;
        this.rejectionReason = reason;
        this.reviewedAt      = LocalDateTime.now();
    }
}