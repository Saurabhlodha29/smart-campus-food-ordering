package com.smartcampus.backend.dto;

import java.time.LocalDateTime;

public class PickupSlotRequest {

    private Long outletId;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private int maxOrders;

    public Long getOutletId() { return outletId; }
    public void setOutletId(Long outletId) { this.outletId = outletId; }

    public LocalDateTime getStartTime() { return startTime; }
    public void setStartTime(LocalDateTime startTime) { this.startTime = startTime; }

    public LocalDateTime getEndTime() { return endTime; }
    public void setEndTime(LocalDateTime endTime) { this.endTime = endTime; }

    public int getMaxOrders() { return maxOrders; }
    public void setMaxOrders(int maxOrders) { this.maxOrders = maxOrders; }
}