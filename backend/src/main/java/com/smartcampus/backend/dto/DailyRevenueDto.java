package com.smartcampus.backend.dto;

public class DailyRevenueDto {
    private String date;       // "2025-04-20"
    private long orderCount;
    private double revenue;

    public DailyRevenueDto(String date, long orderCount, double revenue) {
        this.date = date;
        this.orderCount = orderCount;
        this.revenue = revenue;
    }
    public String getDate()       { return date; }
    public long getOrderCount()   { return orderCount; }
    public double getRevenue()    { return revenue; }
}
