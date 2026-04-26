package com.smartcampus.backend.dto;

import jakarta.validation.constraints.*;

/**
 * Used by POST /api/auth/register — student self-registration.
 * The campus is inferred automatically from the email domain.
 * Role is always STUDENT; cannot self-register as ADMIN or MANAGER.
 */
public class RegisterRequest {

    @NotBlank(message = "Full name is required")
    @Size(max = 120)
    private String fullName;

    @NotBlank(message = "Email is required")
    @Email(message = "Must be a valid email")
    @Size(max = 150)
    private String email;

    @NotBlank(message = "Password is required")
    @Size(min = 6, message = "Password must be at least 6 characters")
    private String password;

    public String getFullName()              { return fullName; }
    public void   setFullName(String v)      { this.fullName = v; }

    public String getEmail()                 { return email; }
    public void   setEmail(String v)         { this.email = v; }

    public String getPassword()              { return password; }
    public void   setPassword(String v)      { this.password = v; }
}