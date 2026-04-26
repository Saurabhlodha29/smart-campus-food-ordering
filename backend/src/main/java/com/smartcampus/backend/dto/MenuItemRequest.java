package com.smartcampus.backend.dto;

public class MenuItemRequest {

    private String name;
    private double price;
    private int    prepTime;
    private Long   outletId;
    /** Optional photo URL — client uploads to cloud storage first. */
    private String photoUrl;

    public String getName()     { return name; }
    public double getPrice()    { return price; }
    public int    getPrepTime() { return prepTime; }
    public Long   getOutletId() { return outletId; }
    public String getPhotoUrl() { return photoUrl; }

    public void setName(String name)         { this.name = name; }
    public void setPrice(double price)       { this.price = price; }
    public void setPrepTime(int prepTime)    { this.prepTime = prepTime; }
    public void setOutletId(Long outletId)   { this.outletId = outletId; }
    public void setPhotoUrl(String photoUrl) { this.photoUrl = photoUrl; }
}