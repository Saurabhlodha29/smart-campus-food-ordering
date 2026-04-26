package com.smartcampus.backend.controller;

import com.smartcampus.backend.domain.Campus;
import com.smartcampus.backend.dto.CampusRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.CampusRepository;
import com.smartcampus.backend.repository.OutletRepository;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Campus management endpoints (SuperAdmin only, except GET /api/campuses).
 *
 * <pre>
 * POST   /api/campuses                      SUPERADMIN — create campus
 * GET    /api/campuses                      Authenticated — list all campuses
 * GET    /api/campuses/{id}                 Authenticated — single campus detail
 * GET    /api/campuses/{id}/outlets         Authenticated — all outlets on a campus
 * POST   /api/campuses/{id}/deactivate      SUPERADMIN — soft-deactivate campus
 * POST   /api/campuses/{id}/reactivate      SUPERADMIN — reactivate campus
 * </pre>
 *
 * Hard delete is intentionally omitted: a campus has users, outlets, orders, and
 * payments attached to it via FK constraints — deleting would cascade destroy all
 * of that data. Deactivate/reactivate is the safe lifecycle instead.
 * A deactivated campus will no longer accept new registrations (email domain check
 * will fail) and its outlets will not appear in student listings.
 */
@RestController
@RequestMapping("/api/campuses")
public class CampusController {

    private final CampusRepository campusRepository;
    private final OutletRepository outletRepository;

    public CampusController(CampusRepository campusRepository,
                            OutletRepository outletRepository) {
        this.campusRepository = campusRepository;
        this.outletRepository = outletRepository;
    }

    // ── Create ────────────────────────────────────────────────────────────────

    @PostMapping
    public Campus createCampus(@RequestBody CampusRequest request) {

        if (campusRepository.existsByEmailDomain(request.getEmailDomain())) {
            throw new ApiException(
                "A campus with email domain '" + request.getEmailDomain() + "' already exists.", 409);
        }

        Campus campus = new Campus();
        campus.setName(request.getName());
        campus.setLocation(request.getLocation());
        campus.setEmailDomain(request.getEmailDomain());
        campus.setStatus("ACTIVE");

        return campusRepository.save(campus);
    }

    // ── Read ──────────────────────────────────────────────────────────────────

    @GetMapping
    public List<Campus> getAllCampuses() {
        return campusRepository.findAll();
    }

    @GetMapping("/{id}")
    public Campus getCampusById(@PathVariable Long id) {
        return campusRepository.findById(id)
                .orElseThrow(() -> new ApiException("Campus not found", 404));
    }

    /**
     * List all outlets on a campus — all statuses included.
     * SuperAdmin uses this to audit outlets when reviewing a campus.
     */
    @GetMapping("/{id}/outlets")
    public Object getOutletsForCampus(@PathVariable Long id) {
        campusRepository.findById(id)
                .orElseThrow(() -> new ApiException("Campus not found", 404));
        return outletRepository.findByCampusId(id);
    }

    // ── Deactivate / Reactivate ────────────────────────────────────────────────

    /**
     * Soft-deactivate a campus.
     * Sets campus status to INACTIVE. Does NOT delete any data.
     *
     * Effects:
     *  - New student registrations with this email domain will be rejected.
     *  - Students on this campus can no longer place orders (OrderService checks outlet status).
     *  - Existing data (users, orders, payments) is fully preserved.
     *
     * Note: This does NOT automatically suspend the campus's outlets.
     * SuperAdmin should suspend individual outlets separately if needed,
     * or a future batch job can handle that.
     */
    @PostMapping("/{id}/deactivate")
    public Map<String, Object> deactivateCampus(@PathVariable Long id) {

        Campus campus = campusRepository.findById(id)
                .orElseThrow(() -> new ApiException("Campus not found", 404));

        if ("INACTIVE".equals(campus.getStatus())) {
            throw new ApiException("Campus is already inactive.", 400);
        }

        campus.setStatus("INACTIVE");
        campusRepository.save(campus);

        long outletCount = outletRepository.findByCampusId(id).size();

        return Map.of(
            "message",     "Campus deactivated. No data has been deleted.",
            "campusId",    campus.getId(),
            "campusName",  campus.getName(),
            "status",      campus.getStatus(),
            "outletCount", outletCount,
            "note",        "Suspend individual outlets separately if you want to stop all ordering."
        );
    }

    @PostMapping("/{id}/reactivate")
    public Map<String, Object> reactivateCampus(@PathVariable Long id) {

        Campus campus = campusRepository.findById(id)
                .orElseThrow(() -> new ApiException("Campus not found", 404));

        if ("ACTIVE".equals(campus.getStatus())) {
            throw new ApiException("Campus is already active.", 400);
        }

        campus.setStatus("ACTIVE");
        campusRepository.save(campus);

        return Map.of(
            "message",    "Campus reactivated.",
            "campusId",   campus.getId(),
            "campusName", campus.getName(),
            "status",     campus.getStatus()
        );
    }
}