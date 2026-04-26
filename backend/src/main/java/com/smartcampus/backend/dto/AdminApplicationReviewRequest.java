package com.smartcampus.backend.dto;

import jakarta.validation.constraints.NotBlank;

/** Body for PATCH /api/admin-applications/{id}/approve or /reject (SUPERADMIN only). */
public class AdminApplicationReviewRequest {

    /** Optional message to the applicant (reason for rejection, or welcome note). */
    private String message;

    /**
     * Temporary password to assign when approving.
     * SuperAdmin communicates this to the new admin via email.
     * Required for approve; ignored for reject.
     */
    private String temporaryPassword;

    public String getMessage()                   { return message; }
    public void   setMessage(String message)     { this.message = message; }

    public String getTemporaryPassword()                         { return temporaryPassword; }
    public void   setTemporaryPassword(String temporaryPassword) { this.temporaryPassword = temporaryPassword; }
}