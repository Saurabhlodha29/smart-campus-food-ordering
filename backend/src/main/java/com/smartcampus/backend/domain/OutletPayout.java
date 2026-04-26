package com.smartcampus.backend.domain;

import jakarta.persistence.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * Records every disbursement made (or attempted) to an outlet.
 *
 * <p>The weekly payout scheduler creates one record per outlet per week.
 * Status flow:
 * <pre>
 *   PENDING → SIMULATED (test mode, no real transfer)
 *           → PROCESSING (Razorpay X payout initiated)
 *           → PAID       (Razorpay webhook confirmed)
 *           → FAILED     (Razorpay webhook reported failure)
 * </pre>
 *
 * <h3>Online vs Cash (COD) split</h3>
 * Only ONLINE orders pass through the platform's Razorpay account, so only
 * {@code grossAmount} (online revenue) results in an actual bank transfer to
 * the manager. COD orders are paid directly by the student to the manager in
 * cash at pickup — the platform never holds that money.
 *
 * {@code cashGrossAmount} and {@code cashOrderCount} are recorded for
 * transparency and reporting purposes only — they do NOT affect the transfer
 * amount. The admin dashboard can show managers their total revenue
 * (online + cash) while the payout transfer is always based on online only.
 */
@Entity
@Table(name = "outlet_payouts")
public class OutletPayout {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "outlet_id", nullable = false)
    private Outlet outlet;

    // ── Online revenue (actual payout basis) ─────────────────────────────────

    /** Sum of totalAmount for all PICKED + ONLINE + PAID orders in the period. */
    @Column(nullable = false)
    private double grossAmount;

    /** Commission rate applied — e.g. 0.05 for 5%. */
    @Column(nullable = false)
    private double commissionRate;

    /** commissionRate × grossAmount. */
    @Column(nullable = false)
    private double commissionAmount;

    /** grossAmount − commissionAmount. This is what the outlet receives via bank transfer. */
    @Column(nullable = false)
    private double netAmount;

    /** Number of PICKED ONLINE orders included in this payout. */
    @Column(nullable = false)
    private int orderCount;

    // ── Cash (COD) revenue — tracking only, no transfer ──────────────────────

    /**
     * Sum of totalAmount for all PICKED + CASH + PAID orders in the period.
     * For reporting/transparency only — no bank transfer is made for this amount
     * since the student pays the manager directly in cash at pickup.
     */
    @Column(nullable = false)
    private double cashGrossAmount = 0.0;

    /**
     * Number of PICKED + CASH orders in the period.
     * For reporting/transparency only.
     */
    @Column(nullable = false)
    private int cashOrderCount = 0;

    // ── Razorpay / Status ─────────────────────────────────────────────────────

    /**
     * payout_XXXX from Razorpay X — null when payouts are simulated (test mode)
     * or while still PENDING.
     */
    @Column(length = 100)
    private String razorpayPayoutId;

    /** PENDING | SIMULATED | PROCESSING | PAID | FAILED */
    @Column(nullable = false, length = 20)
    private String status;

    /** Start of the settlement period (inclusive). */
    @Column(nullable = false)
    private LocalDate periodStart;

    /** End of the settlement period (inclusive). */
    @Column(nullable = false)
    private LocalDate periodEnd;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @Column
    private LocalDateTime processedAt;

    /** Human-readable note — e.g. "Simulated — Razorpay X not enabled" or failure reason. */
    @Column(length = 300)
    private String note;

    protected OutletPayout() {}

    public OutletPayout(Outlet outlet, double grossAmount, double commissionRate,
                        double commissionAmount, double netAmount, int orderCount,
                        LocalDate periodStart, LocalDate periodEnd) {
        this.outlet           = outlet;
        this.grossAmount      = grossAmount;
        this.commissionRate   = commissionRate;
        this.commissionAmount = commissionAmount;
        this.netAmount        = netAmount;
        this.orderCount       = orderCount;
        this.periodStart      = periodStart;
        this.periodEnd        = periodEnd;
        this.status           = "PENDING";
        this.createdAt        = LocalDateTime.now();
    }

    // ── Getters ───────────────────────────────────────────────────────────────

    public Long          getId()               { return id; }
    public Outlet        getOutlet()           { return outlet; }
    public double        getGrossAmount()      { return grossAmount; }
    public double        getCommissionRate()   { return commissionRate; }
    public double        getCommissionAmount() { return commissionAmount; }
    public double        getNetAmount()        { return netAmount; }
    public int           getOrderCount()       { return orderCount; }
    public double        getCashGrossAmount()  { return cashGrossAmount; }
    public int           getCashOrderCount()   { return cashOrderCount; }
    public String        getRazorpayPayoutId() { return razorpayPayoutId; }
    public String        getStatus()           { return status; }
    public LocalDate     getPeriodStart()      { return periodStart; }
    public LocalDate     getPeriodEnd()        { return periodEnd; }
    public LocalDateTime getCreatedAt()        { return createdAt; }
    public LocalDateTime getProcessedAt()      { return processedAt; }
    public String        getNote()             { return note; }

    // ── Setters ───────────────────────────────────────────────────────────────

    public void setRazorpayPayoutId(String razorpayPayoutId) {
        this.razorpayPayoutId = razorpayPayoutId;
    }

    public void setStatus(String status) {
        this.status      = status;
        this.processedAt = LocalDateTime.now();
    }

    public void setNote(String note) {
        this.note = note;
    }

    public void setCashGrossAmount(double cashGrossAmount) {
        this.cashGrossAmount = cashGrossAmount;
    }

    public void setCashOrderCount(int cashOrderCount) {
        this.cashOrderCount = cashOrderCount;
    }
}