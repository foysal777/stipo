import os
import sys
import django
import random

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'STEPO_BACKEND.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings
from app.models import EmailTemplate

# Recipient email
recipient = "foysal.cse13@gmail.com"

# Generate a 6-digit random OTP
otp_code = str(random.randint(100000, 999999))

# Load template or use default
try:
    email_template = EmailTemplate.objects.first()
except Exception:
    email_template = None

language = 'sv'  # Default language Swedish, but let's send both or Swedish

if email_template:
    subject = email_template.otp_subject_sv
    body_template = email_template.otp_body_sv
else:
    subject = "Din OTP-kod för stipendiesökning"
    body_template = "Hej,\n\nAnvänd denna OTP-kod för att fortsätta din stipendiesökning:\n\n{otp}\n\nTack."

# Format plain message text
message_text = body_template.replace('{otp}', otp_code)

# Format HTML message text
styled_otp_badge = f"""
<div style="font-size: 36px; font-weight: bold; letter-spacing: 6px; color: #1a73e8; background-color: #f8f9fa; padding: 15px 25px; border-radius: 8px; display: inline-block; border: 2px solid #e8eaed; margin: 15px 0;">
    {otp_code}
</div>
"""
html_content = body_template.replace('{otp}', styled_otp_badge).replace('\n', '<br>')

otp_html = f"""
<div style="font-family: Arial, sans-serif; padding: 25px; max-width: 600px; margin: 0 auto; line-height: 1.6; color: #333; border: 1px solid #e8eaed; border-radius: 12px; background-color: #ffffff;">
    <div style="text-align: center; margin-bottom: 20px;">
        <h2 style="color: #1a73e8; margin: 0;">{subject}</h2>
    </div>
    <div style="font-size: 16px; color: #444;">
        {html_content}
    </div>
</div>
"""

print("=" * 60)
print("📧 SENDING REAL OTP EMAIL DIRECTLY VIA DJANGO")
print("=" * 60)
print(f"SMTP Host: {settings.EMAIL_HOST}")
print(f"SMTP Port: {settings.EMAIL_PORT}")
print(f"SMTP User: {settings.EMAIL_HOST_USER}")
print(f"Recipient: {recipient}")
print(f"Generated OTP Code: {otp_code}")
print("-" * 60)

try:
    print("Sending mail...")
    sent = send_mail(
        subject=subject,
        message=message_text,
        html_message=otp_html,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[recipient],
        fail_silently=False
    )
    print(f"✅ Success! Sent {sent} email(s) successfully.")
    print(f"Please check {recipient}'s inbox (and spam folder) for the 6-digit OTP code: {otp_code}")
except Exception as e:
    import traceback
    print("❌ Error sending email!")
    print(f"Error Type: {e.__class__.__name__}")
    print(f"Error Message: {str(e)}")
    print("-" * 60)
    print("Traceback:")
    traceback.print_exc()
print("=" * 60)
