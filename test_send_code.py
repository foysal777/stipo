import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'STEPO_BACKEND.settings')
django.setup()

from app.models import ScholarshipApplicant
from app.views import send_otp_email
from django.conf import settings

email_addr = "pijey69227@fisedo.com"

print("=" * 60)
print(f"📨 SIMULATING apply/ ENDPOINT FOR {email_addr}")
print("=" * 60)

try:
    SITE_CONFIG = settings.SITE_CONFIG

    # Mimic what apply/ does
    applicant, created = ScholarshipApplicant.objects.update_or_create(
        email=email_addr,
        defaults={
            "form_data": {
                "email": email_addr,
                "language": "sv",
                "name": "Test User"
            }
        }
    )

    if created:
        print(f"✅ New applicant created for {email_addr}")
    else:
        print(f"ℹ️  Existing applicant updated for {email_addr}")

    # Check OTP rate limit
    if not applicant.can_send_otp():
        print("❌ OTP rate limit exceeded. Try again after 1 hour.")
        sys.exit(1)

    applicant.admin_verified = bool(SITE_CONFIG and not SITE_CONFIG.admin_check)
    applicant.email_verified = False
    applicant.save()

    # Generate new OTP
    applicant.generate_new_otp()
    print(f"🔑 Generated OTP: {applicant.otp}")

    # Send OTP email
    print(f"📤 Sending OTP to {email_addr}...")
    send_otp_email(applicant, applicant.email)

    print(f"✅ Success! OTP email sent to {email_addr}!")
    print(f"📬 OTP Code: {applicant.otp}")

except Exception as e:
    import traceback
    print("❌ Error!")
    print(f"Type: {e.__class__.__name__}")
    print(f"Message: {str(e)}")
    traceback.print_exc()

print("=" * 60)
