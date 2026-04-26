package com.smartcampus.backend.service;

import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

/**
 * Handles all outbound email for the platform.
 * Methods are @Async — email sending never blocks the HTTP request thread.
 */
@Service
public class EmailService {

    private static final Logger log = LoggerFactory.getLogger(EmailService.class);

    private final JavaMailSender mailSender;

    public EmailService(JavaMailSender mailSender) {
        this.mailSender = mailSender;
    }

    /**
     * Sends the 6-digit OTP verification email to a newly registered user.
     * Called asynchronously so registration response returns instantly.
     *
     * @param toEmail  Recipient email address
     * @param fullName User's full name (for personalisation)
     * @param otpCode  6-digit OTP string
     */
    @Async
    public void sendOtpEmail(String toEmail, String fullName, String otpCode) {
        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");

            helper.setTo(toEmail);
            helper.setSubject("Your SmartCampus Verification Code: " + otpCode);
            helper.setText(buildOtpEmailHtml(fullName, otpCode), true); // true = HTML

            mailSender.send(message);
            log.info("OTP email sent to {}", toEmail);

        } catch (MessagingException e) {
            // Log but don't throw — a failed email shouldn't crash the registration
            // response.
            // The user can use the resend endpoint.
            log.error("Failed to send OTP email to {}: {}", toEmail, e.getMessage());
        }
    }

    /**
     * Builds a professional HTML email body for the OTP.
     * Inline styles used because most email clients strip <style> tags.
     */
    private String buildOtpEmailHtml(String fullName, String otpCode) {
        // Split OTP into individual digit spans for the visual block style
        StringBuilder digitSpans = new StringBuilder();
        for (char c : otpCode.toCharArray()) {
            digitSpans.append(
                    "<span style=\"display:inline-block; width:48px; height:56px; " +
                            "line-height:56px; text-align:center; font-size:28px; font-weight:700; " +
                            "color:#1a1a2e; background:#f0f4ff; border:2px solid #d0d9ff; " +
                            "border-radius:8px; margin:0 4px;\">" + c + "</span>");
        }

        return """
                <!DOCTYPE html>
                <html>
                <body style="margin:0; padding:0; background-color:#f5f7fa; font-family: 'Segoe UI', Arial, sans-serif;">
                  <table width="100%%" cellpadding="0" cellspacing="0" style="background:#f5f7fa; padding: 40px 0;">
                    <tr>
                      <td align="center">
                        <table width="520" cellpadding="0" cellspacing="0"
                               style="background:#ffffff; border-radius:16px; overflow:hidden;
                                      box-shadow: 0 4px 24px rgba(0,0,0,0.08);">

                          <!-- Header -->
                          <tr>
                            <td style="background: linear-gradient(135deg, #667eea 0%%, #764ba2 100%%);
                                       padding: 32px 40px; text-align:center;">
                              <h1 style="margin:0; color:#ffffff; font-size:24px; font-weight:700;
                                         letter-spacing:-0.5px;">🍔 SmartCampus</h1>
                              <p style="margin:6px 0 0; color:rgba(255,255,255,0.85); font-size:14px;">
                                Campus Food Ordering Platform
                              </p>
                            </td>
                          </tr>

                          <!-- Body -->
                          <tr>
                            <td style="padding: 40px 40px 32px;">
                              <p style="margin:0 0 8px; font-size:18px; font-weight:600; color:#1a1a2e;">
                                Hi %s! 👋
                              </p>
                              <p style="margin:0 0 28px; font-size:15px; color:#555; line-height:1.6;">
                                Welcome to SmartCampus! Please verify your email address
                                to activate your account and start ordering.
                              </p>

                              <!-- OTP block -->
                              <div style="text-align:center; margin: 0 0 28px;">
                                <p style="margin:0 0 16px; font-size:13px; color:#888;
                                          text-transform:uppercase; letter-spacing:1px; font-weight:600;">
                                  Your verification code
                                </p>
                                <div>%s</div>
                              </div>

                              <!-- Expiry note -->
                              <div style="background:#fff8e1; border-left:4px solid #ffc107;
                                          border-radius:4px; padding: 12px 16px; margin-bottom:28px;">
                                <p style="margin:0; font-size:13px; color:#856404;">
                                  ⏱ This code expires in <strong>10 minutes</strong>.
                                  Do not share it with anyone.
                                </p>
                              </div>

                              <p style="margin:0; font-size:14px; color:#888; line-height:1.6;">
                                If you didn't create a SmartCampus account, you can safely ignore this email.
                              </p>
                            </td>
                          </tr>

                          <!-- Footer -->
                          <tr>
                            <td style="background:#f8f9fa; padding: 20px 40px; text-align:center;
                                       border-top: 1px solid #eee;">
                              <p style="margin:0; font-size:12px; color:#aaa;">
                                © SmartCampus Platform &nbsp;·&nbsp; This is an automated message, please do not reply.
                              </p>
                            </td>
                          </tr>

                        </table>
                      </td>
                    </tr>
                  </table>
                </body>
                </html>
                """
                .formatted(fullName, digitSpans.toString());
    }
}