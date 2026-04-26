package com.smartcampus.backend.dto;

import jakarta.validation.constraints.*;

/**
 * Form filled by an outlet manager wishing to register their outlet.
 * Submitted to POST /api/outlet-applications (public — no account needed yet).
 *
 * Document fields (fssaiLicenseNumber, gstin, panNumber, bankAccountNumber,
 * bankIfscCode) are optional in the sense that the application can still be
 * submitted without them, but the verification score will be lower and the
 * campus admin will see them as "Not Provided" in the report.
 *
 * In production, the frontend should make all 5 document fields required.
 */
public class OutletApplicationRequest {

    @NotBlank(message = "Manager name is required")
    @Size(max = 120)
    private String managerName;

    @NotBlank(message = "Manager email is required")
    @Email(message = "Must be a valid email")
    @Size(max = 150)
    private String managerEmail;

    @NotBlank(message = "Outlet name is required")
    @Size(max = 150)
    private String outletName;

    private String outletDescription;

    @NotNull(message = "Campus ID is required")
    private Long campusId;

    @Min(value = 1, message = "Average prep time must be at least 1 minute")
    private int avgPrepTime;

    /**
     * URL of the uploaded license document image (FSSAI certificate photo,
     * trade license scan). Store via Supabase Storage or any CDN before submitting.
     */
    @NotBlank(message = "License/legal document photo URL is required")
    @Size(max = 500)
    private String licenseDocUrl;

    /** Optional photo of the outlet premises. */
    @Size(max = 500)
    private String outletPhotoUrl;

    // ── Document verification fields ──────────────────────────────────────────

    /**
     * FSSAI Food Business Operator license number — exactly 14 digits.
     * Example: 10020011004823
     */
    @Size(max = 20, message = "FSSAI number must be at most 20 characters")
    private String fssaiLicenseNumber;

    /**
     * GST Identification Number — 15 alphanumeric characters.
     * Example: 29ABCDE1234F1Z5
     */
    @Size(max = 20, message = "GSTIN must be at most 20 characters")
    private String gstin;

    /**
     * Permanent Account Number — 10 alphanumeric characters.
     * Example: ABCDE1234F
     */
    @Size(max = 15, message = "PAN must be at most 15 characters")
    private String panNumber;

    /**
     * Bank account number — 9 to 18 digits.
     */
    @Size(max = 25, message = "Bank account number must be at most 25 characters")
    private String bankAccountNumber;

    /**
     * IFSC code of the outlet's bank branch — 11 characters.
     * Example: SBIN0001234
     */
    @Size(max = 15, message = "IFSC code must be at most 15 characters")
    private String bankIfscCode;

    // ── Getters / Setters ─────────────────────────────────────────────────────
    public String getManagerName() {
        return managerName;
    }

    public void setManagerName(String v) {
        this.managerName = v;
    }

    public String getManagerEmail() {
        return managerEmail;
    }

    public void setManagerEmail(String v) {
        this.managerEmail = v;
    }

    public String getOutletName() {
        return outletName;
    }

    public void setOutletName(String v) {
        this.outletName = v;
    }

    public String getOutletDescription() {
        return outletDescription;
    }

    public void setOutletDescription(String v) {
        this.outletDescription = v;
    }

    public Long getCampusId() {
        return campusId;
    }

    public void setCampusId(Long v) {
        this.campusId = v;
    }

    public int getAvgPrepTime() {
        return avgPrepTime;
    }

    public void setAvgPrepTime(int v) {
        this.avgPrepTime = v;
    }

    public String getLicenseDocUrl() {
        return licenseDocUrl;
    }

    public void setLicenseDocUrl(String v) {
        this.licenseDocUrl = v;
    }

    public String getOutletPhotoUrl() {
        return outletPhotoUrl;
    }

    public void setOutletPhotoUrl(String v) {
        this.outletPhotoUrl = v;
    }

    public String getFssaiLicenseNumber() {
        return fssaiLicenseNumber;
    }

    public void setFssaiLicenseNumber(String v) {
        this.fssaiLicenseNumber = v;
    }

    public String getGstin() {
        return gstin;
    }

    public void setGstin(String v) {
        this.gstin = v;
    }

    public String getPanNumber() {
        return panNumber;
    }

    public void setPanNumber(String v) {
        this.panNumber = v;
    }

    public String getBankAccountNumber() {
        return bankAccountNumber;
    }

    public void setBankAccountNumber(String v) {
        this.bankAccountNumber = v;
    }

    public String getBankIfscCode() {
        return bankIfscCode;
    }

    public void setBankIfscCode(String v) {
        this.bankIfscCode = v;
    }
}