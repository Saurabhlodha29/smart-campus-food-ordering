package com.smartcampus.backend.dto;

public class OutletRatingRequest {
    /** Must be between 1 and 5. */
    private int stars;
    private String comment;

    public int getStars()         { return stars; }
    public String getComment()    { return comment; }
    public void setStars(int s)   { this.stars = s; }
    public void setComment(String c) { this.comment = c; }
}
