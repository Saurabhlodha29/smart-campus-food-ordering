package com.smartcampus.backend.domain;

import java.time.LocalDateTime;
import jakarta.persistence.*;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties({"hibernateLazyInitializer", "handler"})
@Entity
@Table(name = "menu_items")
public class MenuItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "outlet_id", nullable = false)
    private Outlet outlet;

    @Column(nullable = false, length = 120)
    private String name;

    @Column(nullable = false)
    private double price;

    /** Average prep time in minutes — shown on the ordering screen like Swiggy/Zomato. */
    @Column(nullable = false)
    private int prepTime;

    /**
     * Optional photo URL for the menu item.
     * Client uploads the image to cloud storage (e.g. Cloudinary/S3)
     * and sends back the URL.
     */
    @Column(length = 500)
    private String photoUrl;

    /**
     * Controls visibility on the ordering screen.
     * Manager marks false when item is out of stock or removed temporarily.
     */
    @Column(nullable = false)
    private boolean isAvailable = true;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    protected MenuItem() {}

    public MenuItem(Outlet outlet, String name, double price, int prepTime) {
        this.outlet    = outlet;
        this.name      = name;
        this.price     = price;
        this.prepTime  = prepTime;
    }

    public MenuItem(Outlet outlet, String name, double price, int prepTime, String photoUrl) {
        this(outlet, name, price, prepTime);
        this.photoUrl = photoUrl;
    }

    @PrePersist
    public void prePersist() {
        this.createdAt = LocalDateTime.now();
    }

    // ── Getters ───────────────────────────────────────────────────────────────
    public Long    getId()       { return id; }
    public Outlet  getOutlet()   { return outlet; }
    public String  getName()     { return name; }
    public double  getPrice()    { return price; }
    public int     getPrepTime() { return prepTime; }
    public String  getPhotoUrl() { return photoUrl; }
    public boolean isAvailable() { return isAvailable; }
    public LocalDateTime getCreatedAt() { return createdAt; }

    // ── Setters (used by manager for menu editing) ────────────────────────────
    public void setName(String name)         { this.name = name; }
    public void setPrice(double price)       { this.price = price; }
    public void setPrepTime(int prepTime)    { this.prepTime = prepTime; }
    public void setPhotoUrl(String photoUrl) { this.photoUrl = photoUrl; }
    public void setAvailable(boolean available) { this.isAvailable = available; }
}