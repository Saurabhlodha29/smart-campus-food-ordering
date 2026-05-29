package com.smartcampus.backend.service;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * SSE registry backed by Redis pub/sub.
 *
 * Flow:
 *   Manager calls updateOrderStatus(orderId, "READY")
 *   → OrderService calls sseEmitterRegistry.pushStatusUpdate(orderId, "READY")
 *   → This class publishes to Redis channel "order-status:{orderId}"
 *   → Redis broadcasts to ALL Spring Boot instances
 *   → Each instance's onRedisMessage() checks if IT holds that emitter
 *   → The instance that holds the student's connection sends the SSE event
 *
 * This makes SSE work correctly across any number of horizontally-scaled instances.
 */
@Component
public class SseEmitterRegistry {

    /** In-memory map — only holds emitters for connections on THIS instance. */
    private final Map<Long, SseEmitter> emitters = new ConcurrentHashMap<>();
    private final StringRedisTemplate redis;

    public SseEmitterRegistry(StringRedisTemplate redis) {
        this.redis = redis;
    }

    public SseEmitter createEmitter(Long orderId) {
        SseEmitter emitter = new SseEmitter(10 * 60 * 1000L);
        emitters.put(orderId, emitter);
        emitter.onCompletion(() -> emitters.remove(orderId));
        emitter.onTimeout(() -> emitters.remove(orderId));
        emitter.onError(e -> emitters.remove(orderId));
        return emitter;
    }

    /**
     * Called by OrderService when an order status changes.
     * Publishes to Redis — received by all instances via onRedisMessage().
     */
    public void pushStatusUpdate(Long orderId, String newStatus) {
        String channel = "order-status:" + orderId;
        String payload = "{\"orderId\":" + orderId + ",\"status\":\"" + newStatus + "\"}";
        try {
            redis.convertAndSend(channel, payload);
        } catch (Exception e) {
            // Redis unavailable — fall back to local-only delivery
            deliverToLocalEmitter(orderId, newStatus, payload);
        }
    }

    /**
     * Called by RedisConfig's RedisMessageListenerContainer when a message arrives
     * on any "order-status:*" channel. Checks if THIS instance holds that emitter.
     */
    public void onRedisMessage(String payload, String channel) {
        // channel = "order-status:42" — extract orderId
        String[] parts = channel.split(":");
        if (parts.length < 2) return;
        try {
            Long orderId = Long.parseLong(parts[1]);
            String status = extractStatus(payload);
            deliverToLocalEmitter(orderId, status, payload);
        } catch (NumberFormatException ignored) {}
    }

    private void deliverToLocalEmitter(Long orderId, String status, String payload) {
        SseEmitter emitter = emitters.get(orderId);
        if (emitter == null) return;  // not connected to this instance
        try {
            emitter.send(SseEmitter.event().name("status").data(payload));
            if ("PICKED".equals(status) || "CANCELLED".equals(status) || "EXPIRED".equals(status)) {
                emitter.complete();
                emitters.remove(orderId);
            }
        } catch (IOException e) {
            emitters.remove(orderId);
        }
    }

    private String extractStatus(String payload) {
        // payload = {"orderId":42,"status":"READY"} — quick parse without JSON library
        int idx = payload.indexOf("\"status\":\"");
        if (idx < 0) return "";
        int start = idx + 10;
        int end = payload.indexOf("\"", start);
        return end > start ? payload.substring(start, end) : "";
    }
}
