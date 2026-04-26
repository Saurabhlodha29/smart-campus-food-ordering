package com.smartcampus.backend.dto;

/**
 * All fields are optional — only non-null values will be applied.
 * Used by PATCH /api/menu-items/{id}  (MANAGER only).
 */
public class MenuItemUpdateRequest {

    private String  name;
    private Double  price;
    private Integer prepTime;
    private String  photoUrl;

    public String  getName()     { return name; }
    public Double  getPrice()    { return price; }
    public Integer getPrepTime() { return prepTime; }
    public String  getPhotoUrl() { return photoUrl; }

    public void setName(String name)         { this.name = name; }
    public void setPrice(Double price)       { this.price = price; }
    public void setPrepTime(Integer prepTime){ this.prepTime = prepTime; }
    public void setPhotoUrl(String photoUrl) { this.photoUrl = photoUrl; }
}