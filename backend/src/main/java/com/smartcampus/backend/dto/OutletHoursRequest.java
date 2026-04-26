package com.smartcampus.backend.dto;

import java.time.LocalTime;

public class OutletHoursRequest {
    /** Format: "HH:mm" e.g. "08:00". Send null to remove the time restriction. */
    private LocalTime openingTime;
    private LocalTime closingTime;

    public LocalTime getOpeningTime() { return openingTime; }
    public LocalTime getClosingTime() { return closingTime; }
    public void setOpeningTime(LocalTime t) { this.openingTime = t; }
    public void setClosingTime(LocalTime t) { this.closingTime = t; }
}
