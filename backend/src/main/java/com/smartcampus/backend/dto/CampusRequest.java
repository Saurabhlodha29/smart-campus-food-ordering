package com.smartcampus.backend.dto;

public class CampusRequest {

    private String name;
    private String location;
    private String emailDomain;

    public String getName() {
        return name;
    }

    public String getLocation() {
        return location;
    }

    public String getEmailDomain() {
        return emailDomain;
    }

    public void setName(String name) {
        this.name = name;
    }

    public void setLocation(String location) {
        this.location = location;
    }

    public void setEmailDomain(String emailDomain) {
        this.emailDomain = emailDomain;
    }
}