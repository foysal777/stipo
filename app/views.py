from dotenv import load_dotenv

import app
load_dotenv()
import jwt
import json
import os

import uuid
import datetime
from django.shortcuts import render
from django.conf import settings
from django.core.mail import send_mail
from django.core.files import File
from django.db import models

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.generics import get_object_or_404
from rest_framework.exceptions import ValidationError

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

import stripe

from .serializers import MockSerializer, ReviewSerializer, PreDefinedScholarshipSerializer #, ScholarshipApplicantSerializer
from . import ai_utils
import Stipo54
# from . import stepo_47rag
from . import report_utils
from .models import ScholarshipApplicant, Review, FAQ, Coupon, PreDefinedScholarship

data = {
        "user_profile": {
            "name": "Anna Karlsson",
            "email": "anna@example.com",
            "gender": "Kvinna",
            "age": 23,
            "level": "Universitet",
            "athlete": "Nej",
            "municipality": "Stockholm"
        },
        "eligible_scholarships": [
            {
                "Namn": "Knut och Alice Wallenbergs Stiftelse",
                "Huvudadress": "Box 16066",
                "Postnr": 10322,
                "Postort": "STOCKHOLM",
                "Telefon": "08-54501780",
                "Län": "Stockholms län",
                "Kommun": "Stockholm",
                "Tillgångar": 6899855000,
                "Ändamål": "Att främja vetenskaplig forskning och undervisnings- eller studieverksamhet av landsgagnelig innebörd...",
            },
            {
                "Namn": "Nordea Sveriges Vinstandelsstiftelse",
                "Huvudadress": "M514",
                "Postnr": "105 71",
                "Postort": "STOCKHOLM",
                "Telefon": "010-1571863",
                "Län": "Stockholms län",
                "Kommun": "Stockholm",
                "Tillgångar": 1990073000,
                "Ändamål": "Stiftelsens ändamål skall vara att ge Nordea Bank Abp:s personal i Sverige delägarintresse...",
            }
        ]
    }


def build_report_for_application(application):
    if application.report_file:
        return application.success_count

    language = application.form_data['language']
    print(F"DEBUGING LANGUAGE: {language}")

    subject = (
        education_level_option
        if (education_level_option := application.form_data.get('education_level_option'))
        else application.form_data.get('education_level_other')
    )

    print("DEBUGING ROLE *******************  ", application.form_data['role'])
    print("DEBUGING ROLE *******************  ", application.form_data.get('elite_athlete'))
    report_data = Stipo54.find_scholarships_v2(
        user_purpose=application.form_data['purpose_of_funding'],
        gender=application.form_data.get('gender')
    )

    report_data = Stipo54.format_scholarship_json(
        report_data,
        output_language=language
    )

    pdf_location = f"{str(uuid.uuid4())}.pdf"

    predefined = PreDefinedScholarship.objects.all()

    if application.form_data['role'] == 'Organisation':
        predefined_always = PreDefinedScholarship.objects.filter(sport__isnull=False, sport='always')
    else:
        predefined_always = PreDefinedScholarship.objects.filter(subject__isnull=False, subject='always')

    if application.form_data['role'] == 'Organisation':
        predefined = predefined.filter(sport__isnull=False)
        application.form_data['education_level_option'] = []

        if 'Football' in application.form_data['sport'] or 'Fotboll' in application.form_data['sport']:
            predefined = predefined.filter(sport="football")
        elif 'Athletics' in application.form_data['sport'] or 'Friidrott' in application.form_data['sport']:
            predefined = predefined.filter(sport="athletics")
        elif 'Golf' in application.form_data['sport']:
            predefined = predefined.filter(sport="golf")
        elif 'Gymnastics' in application.form_data['sport'] or 'Gymnastik' in application.form_data['sport']:
            predefined = predefined.filter(sport="gymnastics")
        elif 'Floorball' in application.form_data['sport'] or 'Innebandy' in application.form_data['sport']:
            predefined = predefined.filter(sport="floorball")
        elif 'Ice Hockey' in application.form_data['sport'] or 'Ishockey' in application.form_data['sport']:
            predefined = predefined.filter(sport="ice_hockey")
        elif (
            'Swimming' in application.form_data['sport']
            or 'Simidrott' in application.form_data['sport']
            or 'Simning' in application.form_data['sport']
        ):
            predefined = predefined.filter(sport="swimming")
        elif 'Handball' in application.form_data['sport'] or 'Handboll' in application.form_data['sport']:
            predefined = predefined.filter(sport="handball")
        elif 'Equestrian' in application.form_data['sport'] or 'Ridsport' in application.form_data['sport']:
            predefined = predefined.filter(sport="equestrian")
        elif (
            'Motorsports' in application.form_data['sport']
            or 'Motorsport' in application.form_data['sport']
            or 'Snowmobile' in application.form_data['sport']
            or 'Snöskoter' in application.form_data['sport']
        ):
            predefined = predefined.filter(sport="motorsports")
    else:
        predefined = predefined.filter(sport__isnull=True)

        if "Economics" in application.form_data['education_level_option'] \
            or "Ekonomiprogrammet" in application.form_data['education_level_option']:
            print("DEBUG <<< ING >>>")
            print(json.dumps(PreDefinedScholarshipSerializer(predefined, many=True).data, indent=2))
            predefined = predefined.filter(subject="economics")
            print("DEBUG <<< ING >>>")
            print(json.dumps(PreDefinedScholarshipSerializer(predefined, many=True).data, indent=2))
            predefined = predefined.exclude(subject='always')
        elif "Engineering" in application.form_data['education_level_option'] \
            or "Teknik och ingenjörsvetenskap" in application.form_data['education_level_option']:
            predefined = predefined.filter(subject="engineering")
            predefined = predefined.exclude(subject='always')
        elif "Law" in application.form_data['education_level_option'] \
            or "Juridik" in application.form_data['education_level_option']:
            predefined = predefined.filter(subject="law")
            predefined = predefined.exclude(subject='always')
        else:
            predefined = predefined.exclude(subject__in=["economics", "engineering", "law", "socialSciences"])
            predefined = predefined.exclude(subject__in=['always'])

    predefined_scholarships = PreDefinedScholarshipSerializer(
        predefined_always, many=True
    ).data + PreDefinedScholarshipSerializer(
        predefined, many=True
    ).data

    total_result = Stipo54.format_scholarship_json(
        predefined_scholarships,
        output_language=language
    ) + report_data[:10 - len(predefined_scholarships)]

    if 'include_municipality_filter' in application.form_data:
        application.form_data.pop('include_municipality_filter')

    report_utils.create_pdf(
        total_result,
        application.form_data,
        settings.WATERMARK_PATH,
        pdf_location
    )

    with open(pdf_location, 'rb') as file:
        application.report_file.save(application.email, File(file), save=True)

    application.success_count = len(report_data)
    application.save()
    os.remove(pdf_location)

    return len(report_data[:10 - len(predefined_scholarships)]) + len(predefined_scholarships)

def get_otp_email_content(otp, language='en'):
    if language == 'sv':
        subject = "Din verifieringskod"
        html_message = f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">
            <h2 style="color: #333;">Verifieringskod</h2>
            <p style="font-size: 16px; color: #555;">Tack för din ansökan! Använd koden nedan för att verifiera din e-postadress.</p>
            <div style="font-size: 36px; font-weight: bold; margin: 20px auto; padding: 15px; background-color: #f4f4f4; border: 1px solid #ddd; border-radius: 8px; display: inline-block; letter-spacing: 5px; color: #000;">
                {otp}
            </div>
            <p style="font-size: 14px; color: #888;">Om du inte begärde detta, vänligen ignorera detta e-postmeddelande.</p>
        </div>
        """
        message = f"Här är din OTP: {otp}"
    else:
        subject = "Your Verification Code"
        html_message = f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">
            <h2 style="color: #333;">Verification Code</h2>
            <p style="font-size: 16px; color: #555;">Thank you for your application! Please use the code below to verify your email address.</p>
            <div style="font-size: 36px; font-weight: bold; margin: 20px auto; padding: 15px; background-color: #f4f4f4; border: 1px solid #ddd; border-radius: 8px; display: inline-block; letter-spacing: 5px; color: #000;">
                {otp}
            </div>
            <p style="font-size: 14px; color: #888;">If you didn't request this, please ignore this email.</p>
        </div>
        """
        message = f"Here is your OTP: {otp}"
    return subject, message, html_message

@api_view(['post'])
def submit_application(request):
    SITE_CONFIG = settings.SITE_CONFIG

    email = request.data.get('email')
    form_data = request.data

    # if application_type in ('organization', 'Organisation'):
    #     profile = {
    #         f"{application_type}": request.data.get('organization_name'),

    #     }

    application, _created = ScholarshipApplicant.objects.update_or_create(
        email=request.data.get('email'),
        defaults={
            "form_data": form_data
        }
    )
    application.admin_verified = bool(SITE_CONFIG and not SITE_CONFIG.admin_check)
    application.email_verified = False
    print("DEBUG ADMIN VER...: ", application.admin_verified)
    
    language = application.form_data.get('language', 'en')
    subject, message, html_message = get_otp_email_content(application.otp, language)
    
    send_mail(
        subject=subject,
        message=message,
        html_message=html_message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[application.email]
    )
    #     Thread(
    #     target=send_mail,
    #     kwargs={
    #         "subject": email_subject,
    #         "message": f"your password reset otp: {user.otp}",
    #         "html_message": email_body,
    #         "from_email": settings.EMAIL_HOST_USER,
    #         "recipient_list": [email],
    #         "fail_silently": False,
    #     }
    # ).start()
    application.save()
    return Response({"msg": "your form is submitted"})


@api_view(['post'])
def send_verification_code(request, email):
    # email = request.data.get('email')
    application = get_object_or_404(ScholarshipApplicant, email=email)
    
    language = application.form_data.get('language', 'en')
    subject, message, html_message = get_otp_email_content(application.otp, language)
    
    send_mail(
        subject=subject,
        message=message,
        html_message=html_message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email]
    )
    return Response({
        "message": "a message with a verification code"
                   " has been sent to your email."
    })
    pass


@api_view(['post'])
def verify_otp(request):
    email = request.data.get('email')
    otp = request.data.get('otp')

    print("DEBUG PAYLOD OTP:")
    print(email)
    print(otp)
    if email is None:
        raise ValidationError({"error": "email is required"})

    if otp is None:
        raise ValidationError({"error": "otp is required"})
    application = get_object_or_404(ScholarshipApplicant, email=email)
    print('lt: ', application.otp)

    if otp != application.otp:
        raise ValidationError({"error": "invalid otp"})
        pass
    application.email_verified = True
    # ai_utils.find_scholarships(
    #     user_data
    # )
    application.refresh_otp()
    # application.email_verified=True

    verify_token = jwt.encode({
            'email': application.email,
            "exp": datetime.datetime.now(datetime.UTC)\
                   +datetime.timedelta(minutes=500),
        },
        settings.SECRET_KEY,
        algorithm='HS256'
    )
    success_count = build_report_for_application(application)
    application.save()
    return Response({
        "application_token": verify_token,
        "success_count": success_count
    })

@api_view(['post'])
def generate_data(request):
    application_token = request.data.get('application_token')
    if not application_token:
        raise ValidationError({"error": "application was not provided"})

    try:
        payload = jwt.decode(
            application_token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
    except jwt.ExpiredSignatureError as e:
        raise ValidationError({"error": "given token expired"})

    except jwt.PyJWTError as e:
        raise ValidationError({"error": "invalid token"})

    application = get_object_or_404(ScholarshipApplicant, email=payload['email'])
    return Response({
        "success_count": build_report_for_application(application),
    })


@api_view(['post'])
def generate_payment_link(request, email, method):
    # email = request.data.get('email')
    if method not in ['klarna', 'paypal', 'card']:
        raise ValidationError({"error": "invalid payment method."})
    coupon = request.data.get('coupon_code')
    discount = 0

    if coupon:
        if cpn:=Coupon.objects.filter(code=coupon).first():
            print(cpn)
            print(cpn.discount)
            discount = cpn.discount
        else:
            print(coupon)
            raise ValidationError({"error": "invalid copuon"})

    SITE_CONFIG = settings.SITE_CONFIG
    success_url = request.data.get('success_url')
    cancel_url = request.data.get('cancel_url')


    application = get_object_or_404(
        ScholarshipApplicant,
        email=email,
    )
    if not application.email_verified:
        raise ValidationError({"error": "the email is not verified."})
    if application.paid:
        raise ValidationError({
            "error": "you have already paid."
        })

    stripe.api_key = os.environ['STRIPE_SECRET_KEY']
    

    STD_PRICE = 299
    PHD_PRICE = 599
    ORG_PRICE = 1599
    print(application.form_data)
    if application.form_data.get('role', "").lower() in  'privatperson individual':

            price = STD_PRICE
    elif 'phd' in application.form_data.get('study_level', "").lower():
            price = PHD_PRICE
    else:
        price = ORG_PRICE

    print(discount)
    print(price)
    price = price - price*(discount/100)
    session = stripe.checkout.Session.create(
      success_url=success_url if success_url else "https://example.com/success",
      cancel_url=cancel_url if cancel_url else "https://example.com/success?error=payment failed",
      line_items=[{
        "price_data":{
            "currency": "sek",
            "product_data": {
                "name": "application fee"
            },
            "unit_amount": int(float(price)*100)
        },
        "quantity": 1
      }],
      mode="payment",
      # payment_method_types=["klarna"],
      payment_method_types=[method],
      metadata={
        "email": email
      }
    )
    return Response({
        "payment_link": session['url']
    })


def handle_checkout_session_complete(event):
    metadata = event['data']['object']['metadata']

    email = metadata.get('email')
    # subscription_type = metadata.get('subscription_type')

    application = get_object_or_404(ScholarshipApplicant, email=email)

    application.paid = True
    application.save()
    return Response({"msg": "payment accepted"})


@api_view(['post'])
def stripe_payment_webhook(request):
    event = None
    payload = request.body
    sig_header = request.headers.get('STRIPE_SIGNATURE')
    if not sig_header:
        raise ValidationError({"error": "validation signature not found"})

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ['STRIPE_WEBHOOK_SECRET'],
        )

    except ValueError as e:
        return Response({'error': "invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return Response({'error': "invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

    if event['type'] == 'checkout.session.completed':
        return handle_checkout_session_complete(event)

    return Response("")


class ReviewView(APIView):
    def get(self, request):

        reviews = Review.objects.order_by("-stars")
        average_rating = reviews.aggregate(models.Avg('stars', default=0))
        return Response({
            "average_rating": average_rating,
            "reviews": [
                {
                    # "email": review.email,
                    "stars": review.stars,
                    "description": review.description
                } for review in reviews
            ]
        })
        pass


    @extend_schema(request=ReviewSerializer)
    def post(self, request):
        email = request.data.get('email')
        description = request.data.get('description')
        stars = request.data.get('stars')

        review = Review.objects.filter(email=email).first()
        if review:
            raise ValidationError({"error": "Review with the same email already exists."})

        if not isinstance(stars, int):
            raise ValidationError({"error": "stars must be an integer."})

        if not 0<stars<6:
            raise ValidationError({"error": "stars must be between 1 and 5"}) 

        Review.objects.create(
            email=email,
            description=description,
            stars=stars
        )
        return Response({
            "error": "review submitted."
        })

@api_view(['get'])
def faq_list(request):
    faqs = []
    faqs_sv = []

    for faq in FAQ.objects.all():
        faqs.append({
            "question": faq.question,
            "answer": faq.answer,
        })
        faqs_sv.append({
            "question": faq.question_sv,
            "answer": faq.answer_sv
        })

    return Response({
        "faqs": faqs,
        "faqs_sv": faqs_sv
    })




@api_view(['post'])
def generate_data_playground(request):

    application = get_object_or_404(ScholarshipApplicant, email="salmanf4545@gmail.com")
    # if application.report_file:
    #     return Response({
    #         "success_count": application.success_count
    #     })

    location = application.form_data.get('municipality')
    language = application.form_data['language']
    print(F"DEBUGING LANGUAGE: {language}")
    

    # report_data = ai_utils.find_scholarships(
    #     settings.DATASET_PATH,
    #     location,
    #     language,
    #     application.form_data,
    # )


    subject = (
        education_level_option
            if (education_level_option:=application.form_data.get('education_level_option'))
            else application.form_data.get('education_level_other')
    )


    pdf_location = f"{str(uuid.uuid4())}.pdf"

    predefined = PreDefinedScholarship.objects.all()
    
    if application.form_data['role'] == 'Organisation':
        predefined_always = PreDefinedScholarship.objects.filter(sport__isnull = False, sport='always')
    else:
        predefined_always = PreDefinedScholarship.objects.filter(subject__isnull = False, subject='always')


    if application.form_data['role'] == 'Organisation':
        predefined = predefined.filter(is_organization=True)
        application.form_data['education_level_option']=[]


        if 'Football' in application.form_data['sport'] \
                or 'Fotboll' in application.form_data['sport']:
            predefined = predefined.filter(sport="football")
        elif 'Athletics' in application.form_data['sport'] \
                or 'Friidrott' in application.form_data['sport']:
            predefined = predefined.filter(sport="athletics")
        elif 'Golf' in application.form_data['sport']:
            predefined = predefined.filter(sport="golf")
        elif 'Gymnastics' in application.form_data['sport'] \
                or 'Gymnastik' in application.form_data['sport']:
            predefined = predefined.filter(sport="gymnastics")
        elif 'Floorball' in application.form_data['sport'] \
                or 'Innebandy' in application.form_data['sport']:
            predefined = predefined.filter(sport="floorball")
        elif 'Ice Hockey' in application.form_data['sport'] \
                or 'Ishockey' in application.form_data['sport']:
            predefined = predefined.filter(sport="ice_hockey")
        elif 'Swimming' in application.form_data['sport'] \
                or 'Simidrott' in application.form_data['sport'] \
                or 'Simning' in application.form_data['sport']:
            predefined = predefined.filter(sport="swimming")
        elif 'Handball' in application.form_data['sport'] \
                or 'Handboll' in application.form_data['sport']:
            predefined = predefined.filter(sport="handball")
        elif 'Equestrian' in application.form_data['sport'] \
                or 'Ridsport' in application.form_data['sport']:
            predefined = predefined.filter(sport="equestrian")
        elif 'Motorsports' in application.form_data['sport'] \
                or 'Motorsport' in application.form_data['sport'] \
                or 'Snowmobile' in application.form_data['sport'] \
                or 'Snöskoter' in application.form_data['sport']:
            predefined = predefined.filter(sport="motorsports")
    else:
        predefined = predefined.filter(is_organization=False)


        if "Economics" in application.form_data['education_level_option']\
            or "Ekonomiprogrammet" in application.form_data['education_level_option']:

            predefined=predefined.exclude(subject='always')

        elif "Engineering" in application.form_data['education_level_option']\
            or "Teknik och ingenjörsvetenskap" in application.form_data['education_level_option']:
            predefined = predefined.filter(subject="engineering")
            predefined=predefined.exclude(subject='always')

        elif "Law" in application.form_data['education_level_option']\
            or "Juridik" in application.form_data['education_level_option']:
            predefined = predefined.filter(subject="law")
            predefined=predefined.exclude(subject='always')

        else:
            predefined=predefined.exclude(subject__in=["economics", "engineering", "law", "socialSciences"])
            predefined=predefined.exclude(subject__in=['always'])



    predefined_scholarships=MockSerializer(
        predefined_always, many=True
    ).data+MockSerializer(
        predefined, many=True
    ).data



    if 'include_municipality_filter' in application.form_data:
                     application.form_data.pop('include_municipality_filter')


    total_result = Stipo54.format_scholarship_json(
        predefined_scholarships,
        output_language=application.form_data['language']
    )
    report_utils.create_pdf(
        # report_data,
        total_result,
        application.form_data,
        settings.WATERMARK_PATH,
        pdf_location
    )

    with open(pdf_location, 'rb') as file:
        application.report_file.save(application.email, File(file), save=True)

    application.save()
    os.remove(pdf_location)
    message = ""

    return Response({
    })
