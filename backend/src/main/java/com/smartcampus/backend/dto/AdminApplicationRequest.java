package com.smartcampus.backend.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Form filled by a person wishing to become the Campus Admin.
 * Submitted to POST /api/admin-applications (public endpoint).
 */
public class AdminApplicationRequest {

    @NotBlank(message = "Full name is required")
    @Size(max = 120)
    private String fullName;

    /**
     * The applicant's official campus email.
     * Must end with the campus email domain they are claiming.
     */
    @NotBlank(message = "Email is required")
    @Email(message = "Must be a valid email")
    @Size(max = 150)
    private String applicantEmail;

    /**
     * Free-text description of their role/authority at the campus.
     * E.g. "Student Council Mess Secretary" or "Administrative Officer, Catering".
     */
    @NotBlank(message = "Designation/role description is required")
    private String designation;

    /** Cloud URL of uploaded campus ID card photo. */
    @NotBlank(message = "Campus ID card photo URL is required")
    @Size(max = 500)
    private String idCardPhotoUrl;

    @NotBlank(message = "Campus name is required")
    @Size(max = 150)
    private String campusName;

    @NotBlank(message = "Campus location is required")
    @Size(max = 200)
    private String campusLocation;

    /**
     * The official email domain of the campus (e.g. "bennett.edu.in").
     * SuperAdmin verifies this independently.
     */
    @NotBlank(message = "Campus email domain is required")
    @Size(max = 100)
    private String campusEmailDomain;

    // ── Getters / Setters ─────────────────────────────────────────────────────
    public String getFullName()          { return fullName; }
    public void   setFullName(String v)  { this.fullName = v; }

    public String getApplicantEmail()         { return applicantEmail; }
    public void   setApplicantEmail(String v) { this.applicantEmail = v; }

    public String getDesignation()         { return designation; }
    public void   setDesignation(String v) { this.designation = v; }

    public String getIdCardPhotoUrl()         { return idCardPhotoUrl; }
    public void   setIdCardPhotoUrl(String v) { this.idCardPhotoUrl = v; }

    public String getCampusName()         { return campusName; }
    public void   setCampusName(String v) { this.campusName = v; }

    public String getCampusLocation()         { return campusLocation; }
    public void   setCampusLocation(String v) { this.campusLocation = v; }

    public String getCampusEmailDomain()         { return campusEmailDomain; }
    public void   setCampusEmailDomain(String v) { this.campusEmailDomain = v; }
}