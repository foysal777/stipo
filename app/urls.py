from django.urls import path
from .views import (
    submit_application,
    verify_otp,
    generate_payment_link,
    stripe_payment_webhook,
    verify_payment_session,
    generate_data,
    ReviewView,
    faq_list,
    send_verification_code,
    contact_us,
    VerifyCaptchaAPIView,
    CookieConsentAPIView
)

urlpatterns = [
    path("apply/", submit_application),
    path("<str:email>/send_code/", send_verification_code),
    path("verify_otp/", verify_otp),
    path('<str:email>/<str:method>/pay/', generate_payment_link),
    path('payment_callback/', stripe_payment_webhook),
    path('payment_callback', stripe_payment_webhook),
    path('verify_payment/', verify_payment_session),
    path('verify_payment', verify_payment_session),
    path('generate_data/', generate_data),
    path('review/', ReviewView.as_view()),
    path('faqs/', faq_list),
    path('contact/', contact_us),
    path('api/verify-captcha/', VerifyCaptchaAPIView.as_view(), name='verify_captcha'),
    path('api/cookie-consent/', CookieConsentAPIView.as_view(), name='cookie_consent'),
    path('api/consent/', CookieConsentAPIView.as_view(), name='consent'),
]