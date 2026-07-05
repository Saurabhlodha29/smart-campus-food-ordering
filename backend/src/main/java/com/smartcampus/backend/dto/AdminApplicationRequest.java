package com.smartcampus.backend.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Form filled by a person wishing to become the Campus Admin.
 * Submitted to POST /api/admin-applications (public endpoint) — only
 * after the applicant's email has been verified via the OTP endpoints.
 *
 * Note: campusEmailDomain is NOT collected from the client — it is derived
 * automatically on the backend from applicantEmail (everything after '@').
 */
public class AdminApplicationRequest {

    @NotBlank(message = "Full name is required")
    @Size(max = 120)
    private String fullName;

    @NotBlank(message = "Email is required")
    @Email(message = "Must be a valid email")
    @Size(max = 150)
    private String applicantEmail;

    @NotBlank(message = "Designation/role description is required")
    private String designation;

    /**
     * Base64 data-URI of the uploaded campus ID card photo
     * (e.g. "data:image/jpeg;base64,...."). Compressed client-side
     * before being sent — kept as TEXT in the database.
     */
    @NotBlank(message = "Campus ID card photo is required")
    @Size(max = 4_000_000, message = "Photo is too large — please use a smaller image")
    private String idCardPhotoUrl;

    @NotBlank(message = "Campus name is required")
    @Size(max = 150)
    private String campusName;

    @NotBlank(message = "Campus location is required")
    @Size(max = 200)
    private String campusLocation;

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
}
