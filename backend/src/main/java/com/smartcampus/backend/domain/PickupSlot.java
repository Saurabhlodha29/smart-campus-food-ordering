package com.smartcampus.backend.domain;

import jakarta.persistence.*;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.time.LocalDate;
import java.time.LocalDateTime;

@JsonIgnoreProperties({ "hibernateLazyInitializer", "handler" })
@Entity
@Table(name = "pickup_slots")
public class PickupSlot {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "outlet_id", nullable = false)
    private Outlet outlet;

    @Column(nullable = false)
    private LocalDateTime startTime;

    @Column(nullable = false)
    private LocalDateTime endTime;

    /**
     * The calendar date this slot belongs to.
     * Derived from startTime.toLocalDate() at creation.
     * Used by the GET /api/slots endpoint to filter for today's slots only,
     * and by the nightly cleanup scheduler to purge past slots.
     *
     * This column is added to fix the "old slots never deleted" bug —
     * without a date field the backend had no efficient way to filter by day.
     */
    @Column(nullable = false)
    private LocalDate slotDate;

    // Max allowed orders in this slot
    @Column(nullable = false)
    private int maxOrders;

    // Current active orders
    @Column(nullable = false)
    private int currentOrders = 0;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    protected PickupSlot() {
        // JPA only
    }

    public PickupSlot(Outlet outlet,
            LocalDateTime startTime,
            LocalDateTime endTime,
            int maxOrders) {
        this.outlet = outlet;
        this.startTime = startTime;
        this.endTime = endTime;
        this.maxOrders = maxOrders;
        this.slotDate = startTime.toLocalDate(); // derived — always consistent with startTime
        this.createdAt = LocalDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public Outlet getOutlet() {
        return outlet;
    }

    public LocalDateTime getStartTime() {
        return startTime;
    }

    public LocalDateTime getEndTime() {
        return endTime;
    }

    public LocalDate getSlotDate() {
        return slotDate;
    }

    public int getMaxOrders() {
        return maxOrders;
    }

    public int getCurrentOrders() {
        return currentOrders;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public boolean isFull() {
        return this.currentOrders >= this.maxOrders;
    }

    public void incrementCurrentOrders() {
        if (this.currentOrders >= this.maxOrders) {
            throw new RuntimeException("Slot capacity exceeded");
        }
        this.currentOrders++;
    }

    /**
     * Called when an order is cancelled — frees up one slot so another student can
     * book.
     * Guarded against going below zero to prevent data corruption.
     */
    public void decrementCurrentOrders() {
        if (this.currentOrders > 0) {
            this.currentOrders--;
        }
    }

    /**
     * For manager-initiated counter orders: directly set the count
     * without the capacity guard. Manager takes responsibility.
     */
    public void setCurrentOrdersManually(int count) {
        this.currentOrders = count;
    }

    public void setMaxOrders(int maxOrders) {
        this.maxOrders = maxOrders;
    }
}