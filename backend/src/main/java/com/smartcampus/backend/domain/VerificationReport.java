package com.smartcampus.backend.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

/**
 * Stores the automated document verification result for an OutletApplication.
 *
 * Created immediately after the application is saved, populated asynchronously
 * by DocumentVerificationService (typically within a few seconds).
 *
 * Status lifecycle:
 * PENDING → verification is queued / running
 * PASSED → overall score >= 80 (admin can approve with confidence)
 * PARTIAL → score 50–79 (admin should review manually)
 * FAILED → score < 50 (likely fake/invalid documents)
 *
 * This entity is 1-to-1 with OutletApplication.
 * The campus admin sees this report on the review screen.
 */
@Entity
@Table(name = "verification_reports")
public class VerificationReport {

    // ── Overall status constants ──────────────────────────────────────────────
    public static final String STATUS_PENDING = "PENDING";
    public static final String STATUS_PASSED = "PASSED";
    public static final String STATUS_PARTIAL = "PARTIAL";
    public static final String STATUS_FAILED = "FAILED";

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** The application this report belongs to (owning side). */
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "outlet_application_id", nullable = false, unique = true)
    private OutletApplication outletApplication;

    // ── FSSAI ─────────────────────────────────────────────────────────────────

    /** True = FoSCoS confirmed the license is Active. Null = API unavailable. */
    @Column
    private Boolean fssaiVerified;

    /** Business name returned by FoSCoS for this FSSAI number. */
    @Column(length = 200)
    private String fssaiRegisteredName;

    /** Expiry date string as returned by FoSCoS (e.g. "31/12/2026"). */
    @Column(length = 30)
    private String fssaiExpiryDate;

    /**
     * 0.0 – 1.0 score of how well the submitted outlet name matches
     * the FoSCoS registered business name.
     * Null when FoSCoS was unavailable.
     */
    @Column
    private Double fssaiNameMatchScore;

    /** True when the name match score is below 0.5 (suspicious mismatch). */
    @Column(nullable = false)
    private boolean fssaiNameMismatch = false;

    /**
     * Human-readable note from the verifier (e.g. "Invalid format — not 14
     * digits").
     */
    @Column(length = 500)
    private String fssaiNote;

    // ── GSTIN ─────────────────────────────────────────────────────────────────

    /**
     * True = GSTN public API confirmed status is "Active". Null = API unavailable.
     */
    @Column
    private Boolean gstVerified;

    /** Legal business name returned by GSTN. */
    @Column(length = 200)
    private String gstBusinessName;

    /** True when GST name vs submitted outlet name score < 0.5. */
    @Column(nullable = false)
    private boolean gstNameMismatch = false;

    @Column(length = 500)
    private String gstNote;

    // ── PAN ───────────────────────────────────────────────────────────────────

    /** True = PAN format matches the regex [A-Z]{5}[0-9]{4}[A-Z]{1}. */
    @Column(nullable = false)
    private boolean panFormatValid = false;

    @Column(length = 500)
    private String panNote;

    // ── Bank / IFSC ───────────────────────────────────────────────────────────

    /** True = Razorpay IFSC API confirmed the IFSC code exists. */
    @Column
    private Boolean bankIfscValid;

    /** Bank name returned by Razorpay IFSC API (e.g. "State Bank of India"). */
    @Column(length = 100)
    private String bankName;

    /** Branch name returned by Razorpay IFSC API. */
    @Column(length = 150)
    private String bankBranch;

    @Column(length = 500)
    private String bankNote;

    // ── Overall scoring ───────────────────────────────────────────────────────

    /**
     * Composite score out of 100:
     * FSSAI verified → 40 pts (format only → 10 pts)
     * GST verified → 30 pts (format only → 8 pts)
     * PAN format OK → 15 pts
     * IFSC valid → 15 pts
     */
    @Column(nullable = false)
    private int overallScore = 0;

    /** PENDING | PASSED | PARTIAL | FAILED */
    @Column(nullable = false, length = 20)
    private String overallStatus = STATUS_PENDING;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    /** Set when the async verification completes. */
    @Column
    private LocalDateTime completedAt;

    protected VerificationReport() {
    }

    public VerificationReport(OutletApplication outletApplication) {
        this.outletApplication = outletApplication;
        this.createdAt = LocalDateTime.now();
    }

    // ── Getters ───────────────────────────────────────────────────────────────
    public Long getId() {
        return id;
    }

    public OutletApplication getOutletApplication() {
        return outletApplication;
    }

    public Boolean getFssaiVerified() {
        return fssaiVerified;
    }

    public String getFssaiRegisteredName() {
        return fssaiRegisteredName;
    }

    public String getFssaiExpiryDate() {
        return fssaiExpiryDate;
    }

    public Double getFssaiNameMatchScore() {
        return fssaiNameMatchScore;
    }

    public boolean isFssaiNameMismatch() {
        return fssaiNameMismatch;
    }

    public String getFssaiNote() {
        return fssaiNote;
    }

    public Boolean getGstVerified() {
        return gstVerified;
    }

    public String getGstBusinessName() {
        return gstBusinessName;
    }

    public boolean isGstNameMismatch() {
        return gstNameMismatch;
    }

    public String getGstNote() {
        return gstNote;
    }

    public boolean isPanFormatValid() {
        return panFormatValid;
    }

    public String getPanNote() {
        return panNote;
    }

    public Boolean getBankIfscValid() {
        return bankIfscValid;
    }

    public String getBankName() {
        return bankName;
    }

    public String getBankBranch() {
        return bankBranch;
    }

    public String getBankNote() {
        return bankNote;
    }

    public int getOverallScore() {
        return overallScore;
    }

    public String getOverallStatus() {
        return overallStatus;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getCompletedAt() {
        return completedAt;
    }

    // ── Setters (used only by DocumentVerificationService) ───────────────────
    public void setFssaiVerified(Boolean v) {
        this.fssaiVerified = v;
    }

    public void setFssaiRegisteredName(String v) {
        this.fssaiRegisteredName = v;
    }

    public void setFssaiExpiryDate(String v) {
        this.fssaiExpiryDate = v;
    }

    public void setFssaiNameMatchScore(Double v) {
        this.fssaiNameMatchScore = v;
    }

    public void setFssaiNameMismatch(boolean v) {
        this.fssaiNameMismatch = v;
    }

    public void setFssaiNote(String v) {
        this.fssaiNote = v;
    }

    public void setGstVerified(Boolean v) {
        this.gstVerified = v;
    }

    public void setGstBusinessName(String v) {
        this.gstBusinessName = v;
    }

    public void setGstNameMismatch(boolean v) {
        this.gstNameMismatch = v;
    }

    public void setGstNote(String v) {
        this.gstNote = v;
    }

    public void setPanFormatValid(boolean v) {
        this.panFormatValid = v;
    }

    public void setPanNote(String v) {
        this.panNote = v;
    }

    public void setBankIfscValid(Boolean v) {
        this.bankIfscValid = v;
    }

    public void setBankName(String v) {
        this.bankName = v;
    }

    public void setBankBranch(String v) {
        this.bankBranch = v;
    }

    public void setBankNote(String v) {
        this.bankNote = v;
    }

    public void setOverallScore(int v) {
        this.overallScore = v;
    }

    public void setOverallStatus(String v) {
        this.overallStatus = v;
    }

    public void setCompletedAt(LocalDateTime v) {
        this.completedAt = v;
    }
}