package com.smartcampus.backend.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "outlet_ratings",
       uniqueConstraints = @UniqueConstraint(columnNames = {"order_id"}))
public class OutletRating {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "outlet_id", nullable = false)
    private Outlet outlet;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "student_id", nullable = false)
    private User student;

    /** One rating per order — prevents duplicate ratings. */
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id", nullable = false, unique = true)
    private Order order;

    /** 1 to 5 stars. */
    @Column(nullable = false)
    private int stars;

    /** Optional written comment, max 500 chars. */
    @Column(length = 500)
    private String comment;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    protected OutletRating() {}

    public OutletRating(Outlet outlet, User student, Order order, int stars, String comment) {
        this.outlet = outlet;
        this.student = student;
        this.order = order;
        this.stars = stars;
        this.comment = comment;
        this.createdAt = LocalDateTime.now();
    }

    public Long getId()          { return id; }
    public Outlet getOutlet()    { return outlet; }
    public User getStudent()     { return student; }
    public Order getOrder()      { return order; }
    public int getStars()        { return stars; }
    public String getComment()   { return comment; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
