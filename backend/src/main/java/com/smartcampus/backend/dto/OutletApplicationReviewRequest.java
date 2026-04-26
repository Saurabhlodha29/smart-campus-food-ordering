package com.smartcampus.backend.dto;

/** Body for PATCH /api/outlet-applications/{id}/approve or /reject (ADMIN only). */
public class OutletApplicationReviewRequest {

    /** Reason shown to the manager (required on rejection). */
    private String message;

    /**
     * Temporary password for the manager account created on approval.
     * Admin communicates this to the manager via email/phone.
     */
    private String temporaryPassword;

    public String getMessage()                   { return message; }
    public void   setMessage(String message)     { this.message = message; }

    public String getTemporaryPassword()                         { return temporaryPassword; }
    public void   setTemporaryPassword(String temporaryPassword) { this.temporaryPassword = temporaryPassword; }
}