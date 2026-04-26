package com.smartcampus.backend.service;

import com.smartcampus.backend.domain.Notification;
import com.smartcampus.backend.domain.OutletApplication;
import com.smartcampus.backend.domain.VerificationReport;
import com.smartcampus.backend.repository.NotificationRepository;
import com.smartcampus.backend.repository.UserRepository;
import com.smartcampus.backend.repository.VerificationReportRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Map;

/**
 * Document Verification Service — 3-layer free approach.
 *
 * Layer 1: Format validation (DocumentFormatValidator — pure regex, instant,
 * free)
 * Layer 2: Public government / bank APIs
 * - GSTN public taxpayer API (free, no key required)
 * - Razorpay IFSC public API (free, no key required)
 * - FoSCoS FSSAI public search (free public government portal)
 * Layer 3: Name cross-matching (our own string logic, free)
 *
 * This service is called asynchronously right after an OutletApplication is
 * saved.
 * The campus admin will see the completed report when they open the review
 * screen.
 *
 * Scoring (out of 100):
 * FSSAI API-verified → 40 pts (format-only fallback → 10 pts)
 * GSTIN API-verified → 30 pts (format-only fallback → 8 pts)
 * PAN format valid → 15 pts
 * IFSC API-verified → 15 pts
 *
 * >= 80 → PASSED (admin can approve confidently)
 * 50–79 → PARTIAL (admin should review manually)
 * < 50 → FAILED (likely invalid/fake documents)
 */
@Service
public class DocumentVerificationService {

    private static final Logger log = LoggerFactory.getLogger(DocumentVerificationService.class);

    private final VerificationReportRepository reportRepo;
    private final NotificationRepository notifRepo;
    private final UserRepository userRepo;
    private final DocumentFormatValidator formatValidator;
    private final RestTemplate restTemplate;

    public DocumentVerificationService(VerificationReportRepository reportRepo,
            NotificationRepository notifRepo,
            UserRepository userRepo,
            DocumentFormatValidator formatValidator,
            RestTemplate restTemplate) {
        this.reportRepo = reportRepo;
        this.notifRepo = notifRepo;
        this.userRepo = userRepo;
        this.formatValidator = formatValidator;
        this.restTemplate = restTemplate;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ENTRY POINT — called by OutletApplicationController after saving the app
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Kicks off the full verification pipeline asynchronously.
     * Creates a PENDING report immediately, then populates it in the background.
     * The @Async annotation means this returns immediately to the caller —
     * the HTTP response is sent before verification completes.
     */
    @Async
    @Transactional
    public void verifyApplicationAsync(OutletApplication app) {
        log.info("[DocVerify] Starting verification for application id={} outlet='{}'",
                app.getId(), app.getOutletName());

        // Create the report row immediately so the admin can see PENDING status
        VerificationReport report = new VerificationReport(app);
        report = reportRepo.save(report);

        try {
            runVerification(app, report);
        } catch (Exception e) {
            // If anything blows up unexpectedly, mark the report as FAILED
            // so the admin knows something went wrong and can review manually
            log.error("[DocVerify] Unexpected error verifying application id={}: {}",
                    app.getId(), e.getMessage(), e);
            report.setOverallStatus(VerificationReport.STATUS_FAILED);
            report.setFssaiNote("Verification engine error: " + e.getMessage());
            report.setCompletedAt(LocalDateTime.now());
            reportRepo.save(report);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // CORE VERIFICATION LOGIC
    // ─────────────────────────────────────────────────────────────────────────

    private void runVerification(OutletApplication app, VerificationReport report) {

        // ── 1. FSSAI ──────────────────────────────────────────────────────────
        String fssaiNum = app.getFssaiLicenseNumber();
        boolean fssaiFormatOk = fssaiNum != null && formatValidator.validateFssaiFormat(fssaiNum);

        if (!fssaiFormatOk) {
            report.setFssaiVerified(false);
            report.setFssaiNote(fssaiNum == null
                    ? "FSSAI number not provided"
                    : formatValidator.getFssaiFormatError(fssaiNum));
        } else {
            FssaiResult fssai = verifyFssaiViaFoscos(fssaiNum);
            report.setFssaiVerified(fssai.active);
            report.setFssaiRegisteredName(fssai.businessName);
            report.setFssaiExpiryDate(fssai.expiryDate);
            report.setFssaiNote(fssai.note);

            if (fssai.businessName != null) {
                double score = nameMatchScore(app.getOutletName(), fssai.businessName);
                report.setFssaiNameMatchScore(score);
                report.setFssaiNameMismatch(score < 0.5);
                if (score < 0.5) {
                    log.warn("[DocVerify] FSSAI name mismatch: submitted='{}' registered='{}' score={}",
                            app.getOutletName(), fssai.businessName, score);
                }
            }
        }

        // ── 2. GSTIN ─────────────────────────────────────────────────────────
        String gstin = app.getGstin();
        boolean gstFormatOk = gstin != null && formatValidator.validateGstinFormat(gstin);

        if (!gstFormatOk) {
            report.setGstVerified(false);
            report.setGstNote(gstin == null
                    ? "GSTIN not provided"
                    : formatValidator.getGstinFormatError(gstin));
        } else {
            GstResult gst = verifyGstinViaGstn(gstin);
            report.setGstVerified(gst.active);
            report.setGstBusinessName(gst.legalName);
            report.setGstNote(gst.note);

            if (gst.legalName != null) {
                double score = nameMatchScore(app.getOutletName(), gst.legalName);
                report.setGstNameMismatch(score < 0.5);
                if (score < 0.5) {
                    log.warn("[DocVerify] GST name mismatch: submitted='{}' registered='{}' score={}",
                            app.getOutletName(), gst.legalName, score);
                }
            }
        }

        // ── 3. PAN ───────────────────────────────────────────────────────────
        // No free real-time API for PAN — format validation only
        String pan = app.getPanNumber();
        boolean panFormatOk = pan != null && formatValidator.validatePanFormat(pan);
        report.setPanFormatValid(panFormatOk);
        if (pan == null) {
            report.setPanNote("PAN not provided");
        } else {
            report.setPanNote(panFormatOk
                    ? "Format valid (real-time PAN verification requires paid API)"
                    : "Invalid PAN format — expected 5 letters + 4 digits + 1 letter (e.g. ABCDE1234F)");
        }

        // ── 4. Bank / IFSC ───────────────────────────────────────────────────
        String ifsc = app.getBankIfscCode();
        boolean ifscFormatOk = ifsc != null && formatValidator.validateIfscFormat(ifsc);

        if (!ifscFormatOk) {
            report.setBankIfscValid(false);
            report.setBankNote(ifsc == null
                    ? "IFSC code not provided"
                    : "Invalid IFSC format — expected 4 letters + 0 + 6 alphanumeric (e.g. SBIN0001234)");
        } else {
            IfscResult ifscResult = verifyIfscViaRazorpay(ifsc);
            report.setBankIfscValid(ifscResult.valid);
            report.setBankName(ifscResult.bankName);
            report.setBankBranch(ifscResult.branchName);
            report.setBankNote(ifscResult.note);
        }

        // Also validate account number format (no API for this)
        String accNo = app.getBankAccountNumber();
        if (accNo != null && !formatValidator.validateAccountNumberFormat(accNo)) {
            String existing = report.getBankNote();
            report.setBankNote((existing != null ? existing + " | " : "")
                    + "Account number format invalid (expected 9–18 digits)");
        }

        // ── 5. Compute overall score ─────────────────────────────────────────
        int score = 0;

        if (Boolean.TRUE.equals(report.getFssaiVerified()))
            score += 40;
        else if (fssaiFormatOk)
            score += 10; // API unavailable, format OK

        if (Boolean.TRUE.equals(report.getGstVerified()))
            score += 30;
        else if (gstFormatOk)
            score += 8; // API unavailable, format OK

        if (report.isPanFormatValid())
            score += 15;

        if (Boolean.TRUE.equals(report.getBankIfscValid()))
            score += 15;

        report.setOverallScore(score);
        report.setOverallStatus(
                score >= 80 ? VerificationReport.STATUS_PASSED
                        : score >= 50 ? VerificationReport.STATUS_PARTIAL : VerificationReport.STATUS_FAILED);
        report.setCompletedAt(LocalDateTime.now());

        reportRepo.save(report);

        log.info("[DocVerify] Completed for application id={}. Score={} Status={}",
                app.getId(), score, report.getOverallStatus());

        // Notify the campus admin that a new application has been verified
        notifyAdminVerificationComplete(app, report);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // LAYER 2 — Public API calls
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Calls FoSCoS (Food Safety Compliance System) — the official FSSAI portal.
     * Public government endpoint, no API key required.
     * Gracefully falls back to null result if the portal is unreachable.
     */
    @SuppressWarnings("unchecked")
    private FssaiResult verifyFssaiViaFoscos(String licenseNumber) {
        try {
            String url = "https://foscos.fssai.gov.in/api/v1.0/search_lic_reg?lic_no=" + licenseNumber;

            HttpHeaders headers = new HttpHeaders();
            headers.set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
            headers.set("Origin", "https://foscos.fssai.gov.in");
            headers.set("Referer", "https://foscos.fssai.gov.in");

            ResponseEntity<Map> response = restTemplate.exchange(
                    url, HttpMethod.GET, new HttpEntity<>(headers), Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                Map<String, Object> body = response.getBody();
                String status = (String) body.get("license_status");
                String businessName = (String) body.get("business_name");
                String expiryDate = (String) body.get("expiry_date");

                boolean isActive = "Active".equalsIgnoreCase(status)
                        || "active".equalsIgnoreCase(status);

                return new FssaiResult(
                        isActive,
                        businessName,
                        expiryDate,
                        isActive ? "License is Active" : "License status: " + status);
            }
        } catch (HttpClientErrorException.NotFound e) {
            return new FssaiResult(false, null, null, "FSSAI license number not found in FoSCoS database");
        } catch (Exception e) {
            log.warn("[DocVerify] FoSCoS API unavailable for {}: {}", licenseNumber, e.getMessage());
        }
        // Graceful degradation — API unavailable, format was already validated
        return new FssaiResult(null, null, null,
                "FoSCoS portal unreachable — format validated only. Manual verification recommended.");
    }

    /**
     * Calls the official GSTN (GST Network) taxpayer search endpoint.
     * This is a public government API — no key required, but requires
     * browser-like headers to avoid bot detection.
     */
    @SuppressWarnings("unchecked")
    private GstResult verifyGstinViaGstn(String gstin) {
        try {
            String url = "https://services.gst.gov.in/services/api/search/taxpayerDetails?gstin=" + gstin;

            HttpHeaders headers = new HttpHeaders();
            headers.set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
            headers.set("Referer", "https://www.gst.gov.in/");
            headers.set("Accept", "application/json");

            ResponseEntity<Map> response = restTemplate.exchange(
                    url, HttpMethod.GET, new HttpEntity<>(headers), Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                Map<String, Object> body = response.getBody();
                String status = (String) body.get("sts"); // "Active" or "Cancelled"
                String legalName = (String) body.get("lgnm"); // legal name
                String tradeName = (String) body.get("tradeNam"); // trade name

                boolean isActive = "Active".equalsIgnoreCase(status);

                // Use trade name if legal name is blank
                String displayName = (legalName != null && !legalName.isBlank())
                        ? legalName
                        : tradeName;

                return new GstResult(
                        isActive,
                        displayName,
                        isActive ? "GST registration is Active" : "GST status: " + status);
            }
        } catch (HttpClientErrorException.NotFound e) {
            return new GstResult(false, null, "GSTIN not found in GSTN database");
        } catch (Exception e) {
            log.warn("[DocVerify] GSTN API unavailable for {}: {}", gstin, e.getMessage());
        }
        return new GstResult(null, null,
                "GSTN portal unreachable — format validated only. Manual verification recommended.");
    }

    /**
     * Calls Razorpay's free public IFSC database API.
     * No authentication required. Returns bank name, branch, address.
     * Returns invalid result (not an exception) when IFSC doesn't exist.
     */
    @SuppressWarnings("unchecked")
    private IfscResult verifyIfscViaRazorpay(String ifsc) {
        try {
            String url = "https://ifsc.razorpay.com/" + ifsc.toUpperCase();
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                Map<String, Object> body = response.getBody();
                String bank = (String) body.get("BANK");
                String branch = (String) body.get("BRANCH");
                String address = (String) body.get("ADDRESS");

                return new IfscResult(true, bank, branch,
                        "Valid IFSC — " + bank + ", " + branch
                                + (address != null ? " (" + address + ")" : ""));
            }
        } catch (HttpClientErrorException.NotFound e) {
            return new IfscResult(false, null, null,
                    "IFSC code not found in Razorpay's database — verify the code is correct");
        } catch (Exception e) {
            log.warn("[DocVerify] Razorpay IFSC API unavailable for {}: {}", ifsc, e.getMessage());
        }
        return new IfscResult(null, null, null,
                "IFSC API temporarily unavailable — format validated only");
    }

    // ─────────────────────────────────────────────────────────────────────────
    // LAYER 3 — Name cross-matching
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Computes a 0.0–1.0 similarity score between the outlet name submitted
     * by the manager and the registered business name returned by the API.
     *
     * Algorithm: proportion of words in the submitted name that also appear
     * in the registered name (after normalisation).
     *
     * Thresholds:
     * >= 0.7 → Strong match
     * 0.5–0.7 → Likely match
     * < 0.5 → Suspicious mismatch — flag for manual review
     */
    double nameMatchScore(String submittedName, String registeredName) {
        if (submittedName == null || registeredName == null)
            return 0.0;

        String a = normalizeName(submittedName);
        String b = normalizeName(registeredName);

        if (a.equals(b))
            return 1.0;
        if (a.isEmpty() || b.isEmpty())
            return 0.0;

        String[] wordsA = a.split("\\s+");
        if (wordsA.length == 0)
            return 0.0;

        long matchCount = Arrays.stream(wordsA)
                .filter(word -> word.length() > 1) // skip single-char remnants
                .filter(b::contains)
                .count();

        long meaningfulWords = Arrays.stream(wordsA)
                .filter(w -> w.length() > 1)
                .count();

        if (meaningfulWords == 0)
            return 0.0;

        return (double) matchCount / meaningfulWords;
    }

    private String normalizeName(String input) {
        return input.toLowerCase()
                // Remove punctuation
                .replaceAll("[^a-z0-9\\s]", "")
                // Remove common legal suffixes / filler words
                .replaceAll("\\b(pvt|ltd|private|limited|and|the|foods|food|cafe|canteen|kitchen)\\b", "")
                .trim()
                // Collapse multiple spaces
                .replaceAll("\\s+", " ");
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ADMIN NOTIFICATION
    // ─────────────────────────────────────────────────────────────────────────

    private void notifyAdminVerificationComplete(OutletApplication app, VerificationReport report) {
        try {
            // Find the campus admin(s) for this application's campus
            userRepo.findAll().stream()
                    .filter(u -> u.getRole() != null
                            && "ADMIN".equals(u.getRole().getName())
                            && u.getCampus() != null
                            && u.getCampus().getId().equals(app.getCampus().getId()))
                    .forEach(admin -> {
                        String statusEmoji = switch (report.getOverallStatus()) {
                            case VerificationReport.STATUS_PASSED -> "✅";
                            case VerificationReport.STATUS_PARTIAL -> "⚠️";
                            case VerificationReport.STATUS_FAILED -> "❌";
                            default -> "🔄";
                        };

                        String msg = String.format(
                                "New outlet application from %s (%s) has been automatically verified. " +
                                        "Verification result: %s %s (Score: %d/100). " +
                                        "Please review the application and the verification report.",
                                app.getManagerName(),
                                app.getOutletName(),
                                statusEmoji,
                                report.getOverallStatus(),
                                report.getOverallScore());

                        notifRepo.save(new Notification(
                                admin,
                                "New Outlet Application — Verification " + report.getOverallStatus(),
                                msg,
                                Notification.TYPE_OUTLET_APP_APPROVED // reuse closest type
                        ));
                    });
        } catch (Exception e) {
            // Notification failure must never affect the main verification flow
            log.warn("[DocVerify] Failed to notify admin for application id={}: {}",
                    app.getId(), e.getMessage());
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Internal result value objects (private inner records)
    // ─────────────────────────────────────────────────────────────────────────

    /** Null active = API unavailable (degrade gracefully). */
    private record FssaiResult(Boolean active, String businessName, String expiryDate, String note) {
    }

    private record GstResult(Boolean active, String legalName, String note) {
    }

    private record IfscResult(Boolean valid, String bankName, String branchName, String note) {
    }
}