package com.smartcampus.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * Sent by MANAGER to save their bank account details for weekly payouts.
 * These fields are stored on the Outlet entity.
 */
public class OutletBankDetailsRequest {

    @NotBlank
    @Size(min = 9, max = 18)
    @Pattern(regexp = "\\d{9,18}", message = "Account number must be 9–18 digits")
    private String bankAccountNumber;

    @NotBlank
    @Pattern(regexp = "[A-Z]{4}0[A-Z0-9]{6}", message = "Invalid IFSC format — example: SBIN0001234")
    private String bankIfscCode;

    @NotBlank
    @Size(min = 2, max = 120)
    private String bankAccountHolderName;

    public String getBankAccountNumber()    { return bankAccountNumber; }
    public String getBankIfscCode()         { return bankIfscCode; }
    public String getBankAccountHolderName(){ return bankAccountHolderName; }

    public void setBankAccountNumber(String bankAccountNumber) {
        this.bankAccountNumber = bankAccountNumber;
    }
    public void setBankIfscCode(String bankIfscCode) {
        this.bankIfscCode = bankIfscCode;
    }
    public void setBankAccountHolderName(String bankAccountHolderName) {
        this.bankAccountHolderName = bankAccountHolderName;
    }
}