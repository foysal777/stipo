import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'STEPO_BACKEND.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

recipient = "yogenit413@fisedo.com"
subject = "Stepo SMTP Test"
message = "If you receive this, your SMTP settings are correct!"

print("=" * 60)
print("📧 TESTING EMAIL SENDING DIRECTLY VIA DJANGO")
print("=" * 60)
print(f"SMTP Host: {settings.EMAIL_HOST}")
print(f"SMTP Port: {settings.EMAIL_PORT}")
print(f"SMTP User: {settings.EMAIL_HOST_USER}")
print(f"Recipient: {recipient}")
print("-" * 60)

try:
    print("Sending mail...")
    sent = send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[recipient],
        fail_silently=False
    )
    print(f"✅ Success! Sent {sent} email(s) successfully.")
    print("Please check your inbox (including spam folder) for the test email.")
except Exception as e:
    import traceback
    print("❌ Error sending email!")
    print(f"Error Type: {e.__class__.__name__}")
    print(f"Error Message: {str(e)}")
    print("-" * 60)
    print("Traceback:")
    traceback.print_exc()
print("=" * 60)
