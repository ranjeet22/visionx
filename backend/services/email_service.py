"""
VisionX Email Delivery Service
Handles secure delivery of 6-digit OTP codes via SMTP with rich neo-brutalist HTML formatting.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple

from backend import config

logger = logging.getLogger("visionx.email")


def is_smtp_configured() -> bool:
    """Checks whether valid SMTP server settings are configured."""
    return bool(config.SMTP_HOST and config.SMTP_HOST.strip())


def send_otp_email(to_email: str, user_id: str, otp_code: str) -> Tuple[bool, str]:
    """
    Sends a 6-digit verification code to the recipient email.
    Returns (success: bool, message: str).
    """
    if not is_smtp_configured():
        msg = (
            f"[VisionX DEV MODE] SMTP server is not configured in .env. "
            f"Registration OTP for {to_email} (User: {user_id}) is: [{otp_code}] (Valid for 5 minutes). "
            f"To enable real email delivery, configure SMTP_HOST, SMTP_PORT, SMTP_USER, and SMTP_PASSWORD in .env."
        )
        logger.warning(msg)
        print(f"\n======================================================\n{msg}\n======================================================\n")
        return True, "OTP generated (dev mode logged; configure SMTP in .env for production delivery)."

    try:
        subject = f"Your VisionX Verification Code: {otp_code}"
        
        # Plain-text version
        plain_text = f"""Hello {user_id},

Your VisionX email verification code is: {otp_code}

This code will expire in 5 minutes.
If you did not request this registration, please safely ignore this email.

— The VisionX Team
"""

        # Neo-brutalist HTML version matching VisionX aesthetic
        html_text = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background-color: #FBF8F2;
      color: #0B0B0B;
      padding: 24px;
      margin: 0;
    }}
    .card {{
      max-width: 480px;
      margin: 0 auto;
      background: #FFFFFF;
      border: 3px solid #0B0B0B;
      border-radius: 16px;
      box-shadow: 6px 6px 0 #0B0B0B;
      padding: 32px;
    }}
    .header {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 24px;
    }}
    .badge {{
      background: #FFC61A;
      color: #0B0B0B;
      border: 2px solid #0B0B0B;
      padding: 4px 10px;
      font-weight: 800;
      font-size: 14px;
      border-radius: 8px;
    }}
    h1 {{
      font-size: 22px;
      font-weight: 800;
      margin: 0 0 8px 0;
    }}
    p {{
      font-size: 15px;
      line-height: 1.5;
      color: #333333;
    }}
    .otp-box {{
      background: #CFE4FB;
      border: 3px solid #0B0B0B;
      border-radius: 12px;
      box-shadow: 4px 4px 0 #0B0B0B;
      text-align: center;
      padding: 16px;
      margin: 24px 0;
    }}
    .otp-code {{
      font-family: 'Space Mono', monospace, Courier;
      font-size: 36px;
      font-weight: 900;
      letter-spacing: 8px;
      color: #0B0B0B;
    }}
    .footer {{
      margin-top: 24px;
      font-size: 12px;
      color: #777777;
      border-top: 1px dashed #CCCCCC;
      padding-top: 16px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <span class="badge">VisionX Auth</span>
    </div>
    <h1>Verify Your VisionX Account</h1>
    <p>Hi <strong>{user_id}</strong>,</p>
    <p>Welcome to VisionX! Use the 6-digit verification code below to complete your registration and activate your account:</p>
    <div class="otp-box">
      <div class="otp-code">{otp_code}</div>
    </div>
    <p>This code will expire in <strong>5 minutes</strong>. For your security, never share this code with anyone.</p>
    <div class="footer">
      If you did not attempt to register an account on VisionX, please safely disregard this email.
    </div>
  </div>
</body>
</html>
"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.SMTP_FROM
        msg["To"] = to_email

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_text, "html", "utf-8"))

        server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10)
        if config.SMTP_USE_TLS:
            server.starttls()
        if config.SMTP_USER and config.SMTP_PASSWORD:
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.sendmail(config.SMTP_FROM, [to_email], msg.as_string())
        server.quit()

        logger.info(f"OTP email sent successfully to {to_email}")
        return True, "Verification email sent successfully."

    except Exception as e:
        logger.error(f"Failed to send OTP email via SMTP to {to_email}: {e}")
        return False, f"SMTP delivery failed: {str(e)}"
