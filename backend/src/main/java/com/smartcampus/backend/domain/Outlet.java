package com.smartcampus.backend.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.time.LocalTime;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties({"hibernateLazyInitializer", "handler"})
@Entity
@Table(name = "outlets")
public class Outlet {

    /**
     * Status lifecycle:
     *  PENDING_LAUNCH → manager adds menu items → clicks "Launch" → ACTIVE
     *  ACTIVE         → manager toggles closed  → CLOSED    (manager-controlled)
     *  CLOSED         → manager toggles open    → ACTIVE    (manager-controlled)
     *  ACTIVE/CLOSED  → campus admin suspends   → SUSPENDED (admin-imposed)
     *  SUSPENDED      → campus admin reactivates → ACTIVE
     *  ANY            → campus admin deletes    → DELETED   (soft-delete, permanent)
     *
     * CLOSED is manager-controlled (they close for lunch break, end of day, etc.)
     * SUSPENDED is admin-imposed (policy violation, complaint, etc.)
     * DELETED is admin-imposed permanent removal — all history preserved in DB.
     * Students see CLOSED outlets greyed out with "Currently closed" label.
     * Students cannot see SUSPENDED or DELETED outlets at all.
     */
    public static final String STATUS_PENDING_LAUNCH = "PENDING_LAUNCH";
    public static final String STATUS_ACTIVE         = "ACTIVE";
    public static final String STATUS_CLOSED         = "CLOSED";
    public static final String STATUS_SUSPENDED      = "SUSPENDED";
    public static final String STATUS_DELETED        = "DELETED";

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 150)
    private String name;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "campus_id", nullable = false)
    private Campus campus;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "manager_id", nullable = false)
    private User manager;

    /** PENDING_LAUNCH | ACTIVE | CLOSED | SUSPENDED | DELETED */
    @Column(nullable = false, length = 20)
    private String status;

    @Column(nullable = false)
    private int avgPrepTime;

    @Column(length = 500)
    private String photoUrl;

    @Column
    private LocalDateTime launchedAt;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    /** Null means no time restriction — outlet operates on manual toggle only. */
    @Column
    private LocalTime openingTime;

    @Column
    private LocalTime closingTime;

    // ── Payout / Bank Details ─────────────────────────────────────────────────

    @Column(length = 30)
    private String bankAccountNumber;

    @Column(length = 11)
    private String bankIfscCode;

    @Column(length = 150)
    private String bankAccountHolderName;

    @Column(length = 50)
    private String razorpayFundAccountId;

    @Column(length = 50)
    private String razorpayContactId;

    protected Outlet() {}

    public Outlet(String name, Campus campus, User manager, String status, int avgPrepTime) {
        this.name        = name;
        this.campus      = campus;
        this.manager     = manager;
        this.status      = status;
        this.avgPrepTime = avgPrepTime;
        this.createdAt   = LocalDateTime.now();
    }

    public Outlet(String name, Campus campus, User manager, String status,
                  int avgPrepTime, String photoUrl) {
        this(name, campus, manager, status, avgPrepTime);
        this.photoUrl = photoUrl;
    }

    // ── Getters ───────────────────────────────────────────────────────────────
    public Long   getId()           { return id; }
    public String getName()         { return name; }
    public Campus getCampus()       { return campus; }
    public User   getManager()      { return manager; }
    public String getStatus()       { return status; }
    public int    getAvgPrepTime()  { return avgPrepTime; }
    public String getPhotoUrl()     { return photoUrl; }
    public LocalDateTime getLaunchedAt() { return launchedAt; }
    public LocalDateTime getCreatedAt()  { return createdAt; }
    public LocalTime getOpeningTime() { return openingTime; }
    public LocalTime getClosingTime() { return closingTime; }

    public String getBankAccountNumber()     { return bankAccountNumber; }
    public String getBankIfscCode()          { return bankIfscCode; }
    public String getBankAccountHolderName() { return bankAccountHolderName; }
    public String getRazorpayFundAccountId() { return razorpayFundAccountId; }
    public String getRazorpayContactId()     { return razorpayContactId; }

    // ── Setters ───────────────────────────────────────────────────────────────
    public void setStatus(String status)    { this.status = status; }
    public void setAvgPrepTime(int t)       { this.avgPrepTime = t; }
    public void setPhotoUrl(String url)     { this.photoUrl = url; }
    public void setManager(User manager)    { this.manager = manager; }

    public void setBankAccountNumber(String v)     { this.bankAccountNumber = v; }
    public void setBankIfscCode(String v)          { this.bankIfscCode = v; }
    public void setBankAccountHolderName(String v) { this.bankAccountHolderName = v; }
    public void setRazorpayFundAccountId(String v) { this.razorpayFundAccountId = v; }
    public void setRazorpayContactId(String v)     { this.razorpayContactId = v; }
    public void setOpeningTime(LocalTime t) { this.openingTime = t; }
    public void setClosingTime(LocalTime t) { this.closingTime = t; }

    /** Called by the outlet launch endpoint. */
    public void launch() {
        this.status     = STATUS_ACTIVE;
        this.launchedAt = LocalDateTime.now();
    }

    /**
     * Toggle between ACTIVE and CLOSED (manager-controlled).
     * Only valid when outlet is ACTIVE or CLOSED.
     * Returns the new status string.
     */
    public String toggleOpenClose() {
        if (STATUS_ACTIVE.equals(this.status)) {
            this.status = STATUS_CLOSED;
        } else if (STATUS_CLOSED.equals(this.status)) {
            this.status = STATUS_ACTIVE;
        } else {
            throw new IllegalStateException(
                "Cannot toggle open/close from status: " + this.status);
        }
        return this.status;
    }

    /** Returns true when the outlet is accepting orders from students. */
    public boolean isAcceptingOrders() {
        return STATUS_ACTIVE.equals(this.status);
    }

    /** Returns true when all three bank fields required for payouts are present. */
    public boolean hasBankDetails() {
        return bankAccountNumber != null && !bankAccountNumber.isBlank()
            && bankIfscCode != null && !bankIfscCode.isBlank()
            && bankAccountHolderName != null && !bankAccountHolderName.isBlank();
    }

    /**
     * Returns true if orders are allowed right now based on time window.
     * If openingTime or closingTime is null, time check is skipped (manual toggle
     * only).
     */
    public boolean isWithinOperatingHours() {
        if (openingTime == null || closingTime == null)
            return true;
        LocalTime now = LocalTime.now();
        if (openingTime.isBefore(closingTime)) {
            return !now.isBefore(openingTime) && !now.isAfter(closingTime);
        } else {
            // overnight window e.g. 22:00–02:00
            return !now.isBefore(openingTime) || !now.isAfter(closingTime);
        }
    }
}