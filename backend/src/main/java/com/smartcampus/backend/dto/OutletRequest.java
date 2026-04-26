package com.smartcampus.backend.dto;

public class OutletRequest {

    private String name;
    private Long campusId;
    private Long managerId;
    private String status;
    private int avgPrepTime;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Long getCampusId() {
        return campusId;
    }

    public void setCampusId(Long campusId) {
        this.campusId = campusId;
    }

    public Long getManagerId() {
        return managerId;
    }

    public void setManagerId(Long managerId) {
        this.managerId = managerId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public int getAvgPrepTime() {
        return avgPrepTime;
    }

    public void setAvgPrepTime(int avgPrepTime) {
        this.avgPrepTime = avgPrepTime;
    }
}