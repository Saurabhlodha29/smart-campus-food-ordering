package com.smartcampus.backend.dto;

public class RepeatOrderRequest {
    private Long studentId;
    private Long slotId;
    private String paymentMode;

    public Long getStudentId()        { return studentId; }
    public Long getSlotId()           { return slotId; }
    public String getPaymentMode()    { return paymentMode; }
    public void setStudentId(Long id) { this.studentId = id; }
    public void setSlotId(Long id)    { this.slotId = id; }
    public void setPaymentMode(String m) { this.paymentMode = m; }
}
