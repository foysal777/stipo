import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'STEPO_BACKEND.settings')
django.setup()

from app.models import ScholarshipApplicant
from app.views import send_otp_email

email_addr = "larimo7933@fisedo.com"

print("=" * 60)
print(f"📧 SENDING OTP TO {email_addr} VIA DJANGO")
print("=" * 60)

try:
    # 1. Create or retrieve applicant
    applicant, created = ScholarshipApplicant.objects.update_or_create(
        email=email_addr,
        defaults={
            "form_data": {
                "email": email_addr,
                "language": "sv"
            }
        }
    )
    if created:
        print(f"Created new ScholarshipApplicant for {email_addr}")
    else:
        print(f"Using existing ScholarshipApplicant for {email_addr}")

    # 2. Generate new OTP
    applicant.generate_new_otp()
    print(f"Generated new OTP Code: {applicant.otp}")

    # 3. Send email
    print("Calling send_otp_email...")
    send_otp_email(applicant, email_addr)
    print(f"✅ Success! OTP email sent to {email_addr}.")

except Exception as e:
    import traceback
    print("❌ Error sending OTP!")
    print(f"Error Type: {e.__class__.__name__}")
    print(f"Error Message: {str(e)}")
    print("-" * 60)
    print("Traceback:")
    traceback.print_exc()
print("=" * 60)
