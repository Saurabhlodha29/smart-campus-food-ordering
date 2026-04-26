package com.smartcampus.backend.controller;

import com.smartcampus.backend.domain.Notification;
import com.smartcampus.backend.exception.ApiException;
import com.smartcampus.backend.repository.NotificationRepository;
import com.smartcampus.backend.repository.UserRepository;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * In-app notification endpoints.
 *
 * All endpoints are for the currently authenticated user.
 *
 *   GET    /api/notifications            — all notifications (newest first)
 *   GET    /api/notifications/unread     — unread only
 *   GET    /api/notifications/unread-count — just the count (for badge)
 *   PATCH  /api/notifications/{id}/read  — mark one notification read
 *   PATCH  /api/notifications/read-all   — mark all read
 */
@RestController
@RequestMapping("/api/notifications")
public class NotificationController {

    private final NotificationRepository notifRepo;
    private final UserRepository         userRepo;

    public NotificationController(NotificationRepository notifRepo,
                                   UserRepository userRepo) {
        this.notifRepo = notifRepo;
        this.userRepo  = userRepo;
    }

    @GetMapping
    public List<Notification> getAll(Authentication auth) {
        Long userId = resolveUserId(auth);
        return notifRepo.findByUserIdOrderByCreatedAtDesc(userId);
    }

    @GetMapping("/unread")
    public List<Notification> getUnread(Authentication auth) {
        Long userId = resolveUserId(auth);
        return notifRepo.findByUserIdAndIsReadFalse(userId);
    }

    @GetMapping("/unread-count")
    public Map<String, Long> getUnreadCount(Authentication auth) {
        Long userId = resolveUserId(auth);
        return Map.of("count", notifRepo.countByUserIdAndIsReadFalse(userId));
    }

    @PatchMapping("/{id}/read")
    public Map<String, String> markRead(@PathVariable Long id, Authentication auth) {
        Long userId = resolveUserId(auth);
        Notification notif = notifRepo.findById(id)
                .orElseThrow(() -> new ApiException("Notification not found", 404));

        if (!notif.getUser().getId().equals(userId)) {
            throw new ApiException("Access denied", 403);
        }

        notif.markRead();
        notifRepo.save(notif);
        return Map.of("message", "Notification marked as read");
    }

    @PatchMapping("/read-all")
    public Map<String, String> markAllRead(Authentication auth) {
        Long userId = resolveUserId(auth);
        List<Notification> unread = notifRepo.findByUserIdAndIsReadFalse(userId);
        unread.forEach(Notification::markRead);
        notifRepo.saveAll(unread);
        return Map.of("message", "All notifications marked as read", "count", String.valueOf(unread.size()));
    }

    // ─────────────────────────────────────────────────────────────────────────
    private Long resolveUserId(Authentication auth) {
        String email = (String) auth.getPrincipal();
        return userRepo.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", 404))
                .getId();
    }
}