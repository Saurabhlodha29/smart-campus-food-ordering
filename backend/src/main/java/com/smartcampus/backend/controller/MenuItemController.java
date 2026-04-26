package com.smartcampus.backend.controller;

import com.smartcampus.backend.domain.MenuItem;
import com.smartcampus.backend.domain.Outlet;
import com.smartcampus.backend.domain.User;
import com.smartcampus.backend.dto.MenuItemRequest;
import com.smartcampus.backend.dto.MenuItemUpdateRequest;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.MenuItemRepository;
import com.smartcampus.backend.repository.OutletRepository;
import com.smartcampus.backend.repository.UserRepository;
import com.smartcampus.backend.service.MLClient;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Menu item management.
 *
 * Public (authenticated) endpoint:
 * GET /api/menu-items?outletId=X — available items only (students, ordering
 * screen)
 *
 * Shared read endpoint (MANAGER or ADMIN):
 * GET /api/menu-items/all?outletId=X — all items including out-of-stock
 * MANAGER: must own the outlet
 * ADMIN: outlet must be on their campus (read-only — no mutation endpoints
 * allowed)
 *
 * Manager-only mutation endpoints (MANAGER role only):
 * POST /api/menu-items — add item to own outlet
 * PATCH /api/menu-items/{id} — edit name/price/prepTime/photoUrl
 * DELETE /api/menu-items/{id} — permanently remove item
 * PATCH /api/menu-items/{id}/availability — toggle available/out-of-stock
 */
@RestController
@RequestMapping("/api/menu-items")
public class MenuItemController {

    private final MenuItemRepository menuItemRepo;
    private final OutletRepository outletRepo;
    private final UserRepository userRepo;
    private final MLClient mlClient;

    public MenuItemController(MenuItemRepository menuItemRepo,
            OutletRepository outletRepo,
            UserRepository userRepo,
            MLClient mlClient) {
        this.menuItemRepo = menuItemRepo;
        this.outletRepo = outletRepo;
        this.userRepo = userRepo;
        this.mlClient = mlClient;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // GET — available items for an outlet (shown to students on ordering screen)
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * GET /api/menu-items?outletId=X
     * Returns available menu items for a specific outlet (students, ordering
     * screen).
     * If no outletId supplied, returns all available items (admin/debug use).
     */
    @GetMapping
    public List<MenuItem> getMenuItems(@RequestParam(required = false) Long outletId) {
        if (outletId != null) {
            return menuItemRepo.findByOutletIdAndIsAvailableTrue(outletId);
        }
        return menuItemRepo.findAll();
    }

    /**
     * GET /api/menu-items/outlet/{outletId}
     * Explicit path-based version — preferred for Flutter since it is cleaner
     * than query params. Returns available items only (no out-of-stock items shown
     * to students).
     */
    @GetMapping("/outlet/{outletId}")
    public List<MenuItem> getMenuItemsByOutlet(@PathVariable Long outletId) {
        outletRepo.findById(outletId)
                .orElseThrow(() -> new ApiException("Outlet not found", 404));
        return menuItemRepo.findByOutletIdAndIsAvailableTrue(outletId);
    }

    /**
     * GET /api/menu-items/search?q=burger
     * Searches for available menu items by name.
     */
    @GetMapping("/search")
    public List<MenuItem> searchMenuItems(@RequestParam String q) {
        if (q == null || q.trim().length() < 2) {
            throw new ApiException("Search query must be at least 2 characters", 400);
        }
        return menuItemRepo.searchByName(q.trim());
    }

    /**
     * GET /api/menu-items/recommendations?outletId=X
     * Returns personalised food recommendations for the logged-in student.
     */
    @GetMapping("/recommendations")
    public List<MenuItem> getRecommendations(@RequestParam Long outletId, Authentication auth) {
        User student = resolveUser(auth);
        Outlet outlet = outletRepo.findById(outletId)
                .orElseThrow(() -> new ApiException("Outlet not found", 404));

        List<Long> recommendedIds = mlClient.getRecommendations(
                student.getId(),
                outletId,
                outlet.getCampus().getId());

        if (recommendedIds.isEmpty()) {
            return List.of();
        }

        // Fetch the full MenuItem objects for the recommended IDs
        return menuItemRepo.findAllById(recommendedIds);
    }

    /**
     * Full item list including out-of-stock items.
     * Accessible by MANAGER (own outlet) and ADMIN (any outlet on their campus).
     * ADMINs get read-only visibility — they cannot call POST/PATCH/DELETE
     * endpoints.
     */
    @GetMapping("/all")
    public List<MenuItem> getAllMenuItems(@RequestParam(required = false) Long outletId,
            Authentication auth) {
        User caller = resolveUser(auth);
        String roleName = caller.getRole().getName(); // e.g. "ROLE_MANAGER" or "MANAGER"

        boolean isAdmin = roleName.equals("ADMIN") || roleName.equals("ROLE_ADMIN");
        boolean isManager = roleName.equals("MANAGER") || roleName.equals("ROLE_MANAGER");

        if (outletId != null) {
            Outlet outlet = outletRepo.findById(outletId)
                    .orElseThrow(() -> new ApiException("Outlet not found", 404));

            if (isManager) {
                // Manager can only see items for their own outlet
                assertOwnsOutlet(caller, outlet);
            } else if (isAdmin) {
                // Admin can only see items for outlets on their own campus
                assertAdminCampusMatch(caller, outlet);
            }

            return menuItemRepo.findByOutletId(outletId);
        }

        // No outletId supplied
        if (isManager) {
            // Return all items for the manager's own outlet
            var outletOpt = outletRepo.findByManagerId(caller.getId());
            if (outletOpt.isEmpty())
                return List.of();
            return menuItemRepo.findByOutletId(outletOpt.get().getId());
        }

        if (isAdmin) {
            // Admin without outletId: return items for all outlets on their campus
            if (caller.getCampus() == null)
                return List.of();
            List<Outlet> campusOutlets = outletRepo.findByCampusId(caller.getCampus().getId());
            return campusOutlets.stream()
                    .flatMap(o -> menuItemRepo.findByOutletId(o.getId()).stream())
                    .toList();
        }

        return menuItemRepo.findAll();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // POST — Add a new menu item (MANAGER only)
    // ─────────────────────────────────────────────────────────────────────────

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public MenuItem createMenuItem(@RequestBody MenuItemRequest req, Authentication auth) {

        Outlet outlet = outletRepo.findById(req.getOutletId())
                .orElseThrow(() -> new ApiException("Outlet not found", 404));

        User manager = resolveUser(auth);
        assertOwnsOutlet(manager, outlet);

        if (Outlet.STATUS_SUSPENDED.equals(outlet.getStatus())) {
            throw new ApiException("Cannot add items to a suspended outlet", 400);
        }

        MenuItem item = req.getPhotoUrl() != null
                ? new MenuItem(outlet, req.getName(), req.getPrice(), req.getPrepTime(), req.getPhotoUrl())
                : new MenuItem(outlet, req.getName(), req.getPrice(), req.getPrepTime());

        return menuItemRepo.save(item);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PATCH — Edit item details (MANAGER only)
    // ─────────────────────────────────────────────────────────────────────────

    @PatchMapping("/{id}")
    public MenuItem updateMenuItem(@PathVariable Long id,
            @RequestBody MenuItemUpdateRequest req,
            Authentication auth) {

        MenuItem item = menuItemRepo.findById(id)
                .orElseThrow(() -> new ApiException("Menu item not found", 404));

        User manager = resolveUser(auth);
        assertOwnsOutlet(manager, item.getOutlet());

        if (req.getName() != null)
            item.setName(req.getName());
        if (req.getPrice() != null)
            item.setPrice(req.getPrice());
        if (req.getPrepTime() != null)
            item.setPrepTime(req.getPrepTime());
        if (req.getPhotoUrl() != null)
            item.setPhotoUrl(req.getPhotoUrl());

        return menuItemRepo.save(item);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // DELETE — Remove item permanently (MANAGER only)
    // ─────────────────────────────────────────────────────────────────────────

    @DeleteMapping("/{id}")
    public Map<String, String> deleteMenuItem(@PathVariable Long id, Authentication auth) {

        MenuItem item = menuItemRepo.findById(id)
                .orElseThrow(() -> new ApiException("Menu item not found", 404));

        User manager = resolveUser(auth);
        assertOwnsOutlet(manager, item.getOutlet());

        menuItemRepo.delete(item);
        return Map.of("message", "Menu item deleted");
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PATCH — Toggle availability (MANAGER only)
    // Body: { "available": false }
    // ─────────────────────────────────────────────────────────────────────────

    @PatchMapping("/{id}/availability")
    public MenuItem setAvailability(@PathVariable Long id,
            @RequestBody Map<String, Boolean> body,
            Authentication auth) {

        MenuItem item = menuItemRepo.findById(id)
                .orElseThrow(() -> new ApiException("Menu item not found", 404));

        User manager = resolveUser(auth);
        assertOwnsOutlet(manager, item.getOutlet());

        Boolean available = body.get("available");
        if (available == null) {
            throw new ApiException("Request body must contain 'available' (true/false)", 400);
        }

        item.setAvailable(available);
        return menuItemRepo.save(item);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────────────────

    private User resolveUser(Authentication auth) {
        String email = (String) auth.getPrincipal();
        return userRepo.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", 404));
    }

    /** Throws 403 if the caller is not the manager of this outlet. */
    private void assertOwnsOutlet(User manager, Outlet outlet) {
        if (!outlet.getManager().getId().equals(manager.getId())) {
            throw new ApiException("You can only manage items for your own outlet", 403);
        }
    }

    /** Throws 403 if the admin's campus does not match the outlet's campus. */
    private void assertAdminCampusMatch(User admin, Outlet outlet) {
        if (admin.getCampus() == null ||
                !admin.getCampus().getId().equals(outlet.getCampus().getId())) {
            throw new ApiException("You can only view outlets on your own campus", 403);
        }
    }
}