package com.smartcampus.backend.dto;

public class OrderItemResponse {
    private Long menuItemId;
    private String menuItemName;
    private String menuItemPhotoUrl;
    private int quantity;
    private double priceAtOrder;
    private double lineTotal;

    public OrderItemResponse(Long menuItemId, String menuItemName, String menuItemPhotoUrl,
                              int quantity, double priceAtOrder) {
        this.menuItemId = menuItemId;
        this.menuItemName = menuItemName;
        this.menuItemPhotoUrl = menuItemPhotoUrl;
        this.quantity = quantity;
        this.priceAtOrder = priceAtOrder;
        this.lineTotal = priceAtOrder * quantity;
    }

    public Long getMenuItemId()       { return menuItemId; }
    public String getMenuItemName()   { return menuItemName; }
    public String getMenuItemPhotoUrl() { return menuItemPhotoUrl; }
    public int getQuantity()          { return quantity; }
    public double getPriceAtOrder()   { return priceAtOrder; }
    public double getLineTotal()      { return lineTotal; }
}
