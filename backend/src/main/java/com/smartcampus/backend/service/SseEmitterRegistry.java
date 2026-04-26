package com.smartcampus.backend.service;

import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * In-memory registry of SSE emitters keyed by orderId.
 * When an order's status changes, call pushStatusUpdate(orderId, newStatus)
 * and the connected Flutter client receives a push instantly.
 */
@Component
public class SseEmitterRegistry {

    private final Map<Long, SseEmitter> emitters = new ConcurrentHashMap<>();

    public SseEmitter createEmitter(Long orderId) {
        // Timeout: 10 minutes. Flutter reconnects automatically.
        SseEmitter emitter = new SseEmitter(10 * 60 * 1000L);
        emitters.put(orderId, emitter);
        emitter.onCompletion(() -> emitters.remove(orderId));
        emitter.onTimeout(() -> emitters.remove(orderId));
        emitter.onError(e -> emitters.remove(orderId));
        return emitter;
    }

    public void pushStatusUpdate(Long orderId, String newStatus) {
        SseEmitter emitter = emitters.get(orderId);
        if (emitter != null) {
            try {
                emitter.send(SseEmitter.event()
                        .name("status")
                        .data("{\"orderId\":" + orderId + ",\"status\":\"" + newStatus + "\"}"));
                if ("PICKED".equals(newStatus) || "CANCELLED".equals(newStatus)
                        || "EXPIRED".equals(newStatus)) {
                    emitter.complete();
                }
            } catch (IOException e) {
                emitters.remove(orderId);
            }
        }
    }
}
