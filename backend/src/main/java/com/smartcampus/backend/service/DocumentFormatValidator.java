package com.smartcampus.backend.service;

import org.springframework.stereotype.Component;

/**
 * Layer 1 of the 3-layer document verification system.
 *
 * Validates Indian government document number formats using pure regex —
 * completely free, runs instantly, no external API calls.
 *
 * This catches:
 * - Mistyped numbers
 * - Fake / randomly generated numbers (wrong length or character pattern)
 * - Wrong document submitted in the wrong field
 *
 * Format rules are based on official government-issued document specifications.
 */
@Component
public class DocumentFormatValidator {

    /**
     * FSSAI Food Business Operator license number.
     * Format: exactly 14 digits.
     * Example: 10020011004823
     */
    public boolean validateFssaiFormat(String number) {
        return number != null && number.matches("\\d{14}");
    }

    /**
     * GST Identification Number.
     * Format: 15 characters
     * - 2 digits : state code (01–37)
     * - 5 letters : first 5 chars of legal entity's PAN
     * - 4 digits : numeric part of PAN
     * - 1 letter : PAN check character
     * - 1 digit : entity number (1–9 for first registration, then A–Z)
     * - 1 letter : always 'Z'
     * - 1 char : checksum digit or letter
     * Example: 29ABCDE1234F1Z5
     */
    public boolean validateGstinFormat(String gstin) {
        return gstin != null &&
                gstin.matches("^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$");
    }

    /**
     * Permanent Account Number (PAN).
     * Format: 5 uppercase letters + 4 digits + 1 uppercase letter.
     * The 4th letter encodes the taxpayer type (P=individual, C=company, etc.)
     * but we don't validate that here — format check is sufficient for Layer 1.
     * Example: ABCDE1234F
     */
    public boolean validatePanFormat(String pan) {
        return pan != null && pan.matches("[A-Z]{5}[0-9]{4}[A-Z]{1}");
    }

    /**
     * IFSC (Indian Financial System Code).
     * Format: 4 uppercase letters (bank code) + '0' + 6 alphanumeric chars.
     * The 5th character is always zero — this is a mandated RBI format rule.
     * Example: SBIN0001234
     */
    public boolean validateIfscFormat(String ifsc) {
        return ifsc != null && ifsc.matches("[A-Z]{4}0[A-Z0-9]{6}");
    }

    /**
     * Indian bank account number.
     * Format: 9–18 digits (covers all scheduled banks).
     * - SBI: 11 digits
     * - HDFC: 14 digits
     * - ICICI: 12 digits
     * - etc.
     */
    public boolean validateAccountNumberFormat(String accountNo) {
        return accountNo != null && accountNo.matches("\\d{9,18}");
    }

    /**
     * Convenience method — returns a human-readable error message
     * when FSSAI format is invalid, or null if valid.
     */
    public String getFssaiFormatError(String number) {
        if (number == null || number.isBlank())
            return "FSSAI license number is required";
        if (!number.matches("\\d+"))
            return "FSSAI number must contain digits only";
        if (number.length() != 14)
            return "FSSAI number must be exactly 14 digits (got " + number.length() + ")";
        return null; // valid
    }

    /**
     * Convenience method — returns a human-readable error message
     * when GSTIN format is invalid, or null if valid.
     */
    public String getGstinFormatError(String gstin) {
        if (gstin == null || gstin.isBlank())
            return "GSTIN is required";
        if (gstin.length() != 15)
            return "GSTIN must be exactly 15 characters (got " + gstin.length() + ")";
        if (!validateGstinFormat(gstin))
            return "GSTIN format is invalid. Expected: 2-digit state + 5 letters + 4 digits + letter + digit + Z + checksum";
        return null;
    }
}