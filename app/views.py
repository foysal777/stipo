from dotenv import load_dotenv

import app
load_dotenv()
import jwt
import json
import os
from rest_framework import status 
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
from . import stipo54
# from . import stepo_47rag
from . import report_utils
from .models import ScholarshipApplicant, Review, FAQ, Coupon, PreDefinedScholarship, SiteConfig, EmailTemplate, CookieConsentLog
from deep_translator import GoogleTranslator
import re
from urllib.parse import urlparse

# Unicode cleaning regex and replacement map for PDF rendering
_BOX_CLEAN = re.compile(
    r'[\u25A0\u25AA\u25AB\u25FB\u25FC\u25FD\u25FE'  # Geometric shapes (filled/hollow boxes)
    r'\u2500-\u257F'  # Box drawing characters
    r'\u2580-\u259F'  # Block elements
    r'\u2600-\u26FF'  # Miscellaneous symbols (stars, weather, etc.)
    r'\u2B1B\u2B1C\u2B50\u2B55'  # Additional symbols
    r'\u00AD\u200B\u200C\u200D\uFEFF'  # Soft hyphen, zero-width spaces, format characters
    r'\u2028\u2029'  # Line/paragraph separators
    r'\u061C\u200E\u200F'  # Bidirectional formatting
    r'\x00-\x08\x0B\x0C\x0E-\x1F'  # Control characters (except tab, newline, carriage return)
    r'\x7F-\x9F'  # DEL and extended control characters
    r'\u0300-\u036F]'  # Combining diacritical marks
)

# Escape sequence patterns like _x0007_
_ESCAPE_SEQ = re.compile(r'_x[0-9A-Fa-f]{4}_')

_BOX_REPLACE = {
    '\u2018': "'", '\u2019': "'",
    '\u201C': '"', '\u201D': '"',
    '\u2013': '-', '\u2014': '-',
    '\u2026': '...', '\u00AB': '"',
    '\u00BB': '"', '\u00A0': ' ',
    '\u2022': '-',
}

def _clean_raw(text):
    """Remove problematic Unicode characters and escape sequences that cause issues in PDF"""
    if not isinstance(text, str):
        return text
    
    # Remove escape sequences like _x0007_
    text = _ESCAPE_SEQ.sub('', text)
    
    # Remove problematic Unicode characters
    text = _BOX_CLEAN.sub('', text)
    
    # Replace special characters with safe equivalents
    for char, rep in _BOX_REPLACE.items():
        text = text.replace(char, rep)
    
    # Clean up excessive whitespace (multiple spaces/newlines)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def normalize_form_data(form_data):
    """Normalize form_data on submission - maps municipality to proper case"""
    from copy import deepcopy
    from stipo54 import MUNICIPALITY_NAME_MAP
    
    normalized = deepcopy(form_data)
    
    # Normalize municipality name through MUNICIPALITY_NAME_MAP
    if 'municipality' in normalized and normalized['municipality']:
        municipality = normalized['municipality'].lower().strip()
        # Look up in map (key is lowercase, value is proper case)
        if municipality in MUNICIPALITY_NAME_MAP:
            normalized['municipality'] = MUNICIPALITY_NAME_MAP[municipality]
    
    return normalized


def translate_study_level(study_level_text, language='sv'):
    """Translate study level display name based on language
    Example: 'Doktorandstudier' → 'PhD/Doctoral Studies' (en) or stays 'Doktorandstudier' (sv)
    """
    if not study_level_text or not isinstance(study_level_text, str):
        return study_level_text
    
    text_lower = study_level_text.lower()
    
    # Detect PhD level
    if any(t in text_lower for t in ['phd', 'doctoral', 'doktorand', 'forskarutbildning', 'doktorsexamen']):
        return 'PhD/Doctoral Studies' if language == 'en' else 'Doktorandstudier'
    # Detect Master level
    elif any(t in text_lower for t in ['master', 'magister', 'masternivå']):
        return "Master's Studies" if language == 'en' else 'Masterexamen'
    # Detect Bachelor level
    elif any(t in text_lower for t in ['bachelor', 'kandidat', 'grundnivå', 'kandidatnivå']):
        return 'Bachelor Studies' if language == 'en' else 'Kandidatexamen'
    
    return study_level_text


def map_subject_for_phd_display(subject, language='sv'):
    """Map subject to PhD category
    Converts subjects to standard PhD categories for display
    Example: 'Teknik' → 'Teknik och ingenjörsvetenskap' (sv) or 'Engineering/Technology' (en)
    """
    if not subject or not isinstance(subject, str):
        return subject
    
    subject_lower = subject.lower().strip()
    
    # PhD Subject Categories mapping
    phd_categories = {
        'sv': {
            'teknik': 'Teknik och ingenjörsvetenskap',
            'teknologi': 'Teknik och ingenjörsvetenskap',
            'ingenjörsvetenskap': 'Teknik och ingenjörsvetenskap',
            'engineering': 'Teknik och ingenjörsvetenskap',
            'technology': 'Teknik och ingenjörsvetenskap',
            
            'ekonomi': 'Ekonomi',
            'economics': 'Ekonomi',
            'business': 'Ekonomi',
            'företagsekonomi': 'Ekonomi',
            
            'medicin': 'Medicin',
            'medicine': 'Medicin',
            'hälsa': 'Medicin',
            'health': 'Medicin',
            
            'juridik': 'Juridik',
            'law': 'Juridik',
            'legal': 'Juridik',
            
            'konst': 'Konst/Kultur',
            'kultur': 'Konst/Kultur',
            'arts': 'Konst/Kultur',
            'culture': 'Konst/Kultur',
        },
        'en': {
            'teknik': 'Engineering/Technology',
            'teknologi': 'Engineering/Technology',
            'ingenjörsvetenskap': 'Engineering/Technology',
            'engineering': 'Engineering/Technology',
            'technology': 'Engineering/Technology',
            
            'ekonomi': 'Economics',
            'economics': 'Economics',
            'business': 'Economics',
            'företagsekonomi': 'Economics',
            
            'medicin': 'Medicine',
            'medicine': 'Medicine',
            'hälsa': 'Medicine',
            'health': 'Medicine',
            
            'juridik': 'Law',
            'law': 'Law',
            'legal': 'Law',
            
            'konst': 'Arts/Culture',
            'kultur': 'Arts/Culture',
            'arts': 'Arts/Culture',
            'culture': 'Arts/Culture',
        }
    }
    
    # Get the appropriate language mapping
    lang_code = 'en' if language == 'en' else 'sv'
    categories = phd_categories.get(lang_code, {})
    
    # Check if subject matches any PhD category keyword
    for keyword, category in categories.items():
        if keyword in subject_lower:
            return category
    
    # If no match found, return original
    return subject



def clean_profile_for_pdf(form_data):
    """
    Clean form data before sending to PDF:
    - Convert education_level_option/education_level_other to subject field
    - Map municipality names through MUNICIPALITY_NAME_MAP for proper display
    - Translate study level to proper display name
    - For PhD users: map subject to PhD category (e.g., Teknik → Teknik och ingenjörsvetenskap)
    - Remove unwanted fields
    - Return cleaned copy
    """
    from copy import deepcopy
    from stipo54 import MUNICIPALITY_NAME_MAP
    
    cleaned = deepcopy(form_data)
    language = cleaned.get('language', 'sv')
    
    # FIRST: Convert education_level_option or education_level_other to subject
    subject_value = None
    if 'education_level_option' in cleaned and cleaned['education_level_option']:
        edu_opt = cleaned['education_level_option']
        # Handle both list and string formats
        if isinstance(edu_opt, list):
            subject_value = ', '.join([str(s) for s in edu_opt if s])
        else:
            subject_value = str(edu_opt)
    
    if not subject_value and 'education_level_other' in cleaned and cleaned['education_level_other']:
        subject_value = str(cleaned['education_level_other'])
    
    # Set subject field if we found a value
    if subject_value:
        cleaned['subject'] = subject_value
    
    # Map municipality name through MUNICIPALITY_NAME_MAP for proper display (Västervik not vastervik)
    if 'municipality' in cleaned and cleaned['municipality']:
        municipality = cleaned['municipality'].lower().strip()
        # Look up in map (key is lowercase, value is proper case)
        if municipality in MUNICIPALITY_NAME_MAP:
            cleaned['municipality'] = MUNICIPALITY_NAME_MAP[municipality]
    
    # Translate study_level to proper display name
    if 'study_level' in cleaned and cleaned['study_level']:
        study_level_translated = translate_study_level(cleaned['study_level'], language)
        cleaned['study_level'] = study_level_translated
        
        # For PhD level users: map subject to PhD category
        study_level_lower = cleaned['study_level'].lower()
        if any(t in study_level_lower for t in ['phd', 'doctoral']):
            if 'subject' in cleaned and cleaned['subject']:
                cleaned['subject'] = map_subject_for_phd_display(cleaned['subject'], language)
    
    # THEN: Remove unwanted fields
    unwanted_fields = {
        'elite_athlete', 'elitidrottare',
        'sport', 'sport_name', 'sportnamn',
        'education_level_option', 'education_level_other',
        'include_municipality_filter',
        'form_file', 'admin_check'
    }
    
    for field in unwanted_fields:
        cleaned.pop(field, None)
    
    # Remove subject if it's empty
    if 'subject' in cleaned and not cleaned['subject']:
        cleaned.pop('subject', None)
    
    return cleaned

def clean_scholarship_data(scholarships):
    """Recursively clean all string values in scholarship dictionaries"""
    if isinstance(scholarships, list):
        return [clean_scholarship_data(item) for item in scholarships]
    elif isinstance(scholarships, dict):
        cleaned = {}
        for key, value in scholarships.items():
            if isinstance(value, str):
                cleaned[key] = _clean_raw(value)
            elif isinstance(value, (list, dict)):
                cleaned[key] = clean_scholarship_data(value)
            else:
                cleaned[key] = value
        return cleaned
    else:
        return scholarships


# def translate_field(text, target_language="en", source_language="sv", debug=False):
#     """Translate text from Swedish to English using GoogleTranslator"""
#     if not text or not isinstance(text, str):
#         return text
    
#     # Only translate SV→EN (data is stored in Swedish)
#     if target_language.lower() == "en" and source_language.lower() == "sv":
#         try:
#             translated = GoogleTranslator(source_language='sv', target_language='en').translate(text)
#             return translated
#         except Exception as e:
#             print(f"[translate_field] ERROR translating: {e}")
#             return text
    
#     # For any other direction, return unchanged
#     return text

def translate_field(text, target_language="en", source_language="sv", debug=False):
    if not text or not isinstance(text, str):
        return text
    
    # Clean PDF-incompatible and invisible characters from source text
    # BEFORE translation so they don't appear in either language output.
    # U+25A0/U+25AA = black squares already in Pinecone raw data.
    # Other chars cause rendering failures in PDF fonts.
    import re
    CLEAN_PATTERN = re.compile(
        r'[\u25A0\u25AA\u25AB\u25FB\u25FC\u25FD\u25FE'  # black/white squares
        r'\u2B1B\u2B1C\u2B50\u2B55'                      # other geometric shapes
        r'\u00AD'                                          # soft hyphen
        r'\u200B\u200C\u200D\uFEFF'                       # zero-width chars
        r'\u2028\u2029'                                    # line/paragraph separators
        r'\x00-\x08\x0B\x0C\x0E-\x1F]'                  # control characters
    )
    text = CLEAN_PATTERN.sub('', text)
    
    # Replace typographic chars PDF fonts struggle with
    REPLACE_MAP = {
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201C': '"',    # left double quote
        '\u201D': '"',    # right double quote
        '\u2013': '-',    # en dash
        '\u2014': '-',    # em dash
        '\u2026': '...',  # ellipsis
        '\u00AB': '"',    # left angle quote
        '\u00BB': '"',    # right angle quote
        '\u00A0': ' ',    # non-breaking space
        '\u2022': '-',    # bullet
    }
    for char, replacement in REPLACE_MAP.items():
        text = text.replace(char, replacement)
    
    # Now translate if needed
    if target_language.lower() == "en" and source_language.lower() == "sv":
        try:
            translated = GoogleTranslator(
                source_language='sv', target_language='en'
            ).translate(text)
            # Apply same cleaning to translated output in case
            # Google Translate introduces new special chars
            if translated:
                translated = CLEAN_PATTERN.sub('', translated)
                for char, replacement in REPLACE_MAP.items():
                    translated = translated.replace(char, replacement)
            return translated
        except Exception as e:
            print(f"[translate_field] ERROR translating: {e}")
            return text
    
    return text


def translate_predefined_scholarships(scholarships, output_language="en"):
    """Translate Purpose/Ändamål fields and field names in predefined scholarships based on language"""
    
    # Field name translations from English to Swedish
    field_name_translations_sv = {
        "Subject": "Ämne",
        "Purpose": "Ändamål",
        "Municipality": "Kommun",
        "Category": "Kategori",
        "Email": "Epost",
        "Website": "Websida",
        "Phone": "Telefon",
        "Assets": "Tillgångar",
        "MainHuvudadress": "Huvudadress",
        "PostalPostnr": "Postnr",
        "City": "Stad",
        "County": "Län",
        "Sport": "Sport",
        "Name": "Namn",
    }
    
    translated = []
    for idx, sch in enumerate(scholarships):
        sch_copy = sch.copy() if isinstance(sch, dict) else sch
        
        # Handle Swedish language: rename field keys only (data is already in Swedish)
        if output_language.lower() == "sv":
            sch_sv = {}
            for key, value in sch_copy.items():
                # Translate field name if mapping exists, otherwise keep original
                translated_key = field_name_translations_sv.get(key, key)
                # NO translation of Purpose content - it's already in Swedish!
                sch_sv[translated_key] = value
            translated.append(sch_sv)
        
        # Handle English language: translate Purpose from Swedish to English
        elif output_language.lower() == "en":
            # Translate Purpose field from Swedish to English
            if "Purpose" in sch_copy and isinstance(sch_copy.get("Purpose"), str):
                sch_copy["Purpose"] = translate_field(sch_copy["Purpose"], target_language="en", source_language="sv")
            translated.append(sch_copy)
        
        else:
            translated.append(sch_copy)
    
    return translated

def _matches_any(text, terms):
    """
    Whole-word substring match for short terms (≤3 chars),
    plain substring for longer terms.
    Prevents 'it' matching inside 'political', 'entity' etc.
    """
    for term in terms:
        if len(term) <= 3:
            # word boundary match for short terms
            if re.search(r'\b' + re.escape(term) + r'\b', text):
                return True
        else:
            if term in text:
                return True
    return False

def send_otp_email(application, recipient_email):
    # Determine language
    language = 'sv'
    if application.form_data and isinstance(application.form_data, dict):
        language = application.form_data.get('language', 'sv')

    # Fetch configured template
    try:
        email_template = EmailTemplate.objects.first()
    except Exception:
        email_template = None

    if email_template:
        if language == 'en':
            subject = email_template.otp_subject_en
            body_template = email_template.otp_body_en
        else:
            subject = email_template.otp_subject_sv
            body_template = email_template.otp_body_sv
    else:
        # Default fallbacks
        if language == 'en':
            subject = "Your scholarship OTP code"
            body_template = "Hello,\n\nUse this OTP code to continue your scholarship search:\n\n{otp}\n\nThank you."
        else:
            subject = "Din OTP-kod för stipendiesökning"
            body_template = "Hej,\n\nAnvänd denna OTP-kod för att fortsätta din stipendiesökning:\n\n{otp}\n\nTack."

    # Replace placeholder in plain text
    message_text = body_template.replace('{otp}', application.otp)

    # Replace placeholder in HTML with a premium styled OTP badge
    styled_otp_html = f"""
    <div style="font-size: 36px; font-weight: bold; letter-spacing: 6px; color: #1a73e8; background-color: #f8f9fa; padding: 15px 25px; border-radius: 8px; display: inline-block; border: 2px solid #e8eaed; margin: 15px 0;">
        {application.otp}
    </div>
    """
    
    # Replace newlines with <br> for HTML rendering
    html_content = body_template.replace('{otp}', styled_otp_html).replace('\n', '<br>')
    
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

    try:
        send_mail(
            subject=subject,
            message=message_text,
            html_message=otp_html,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[recipient_email]
        )
    except Exception as e:
        raise


@api_view(['post'])
def submit_application(request):
    SITE_CONFIG = settings.SITE_CONFIG

    email = request.data.get('email')
    if email:
        email = str(email).strip().lower()
    form_data = request.data
    if isinstance(form_data, dict):
        form_data = form_data.copy()
        form_data['email'] = email
    
    # Normalize municipality and other form fields on submission
    form_data = normalize_form_data(form_data)

    # Check OTP rate limit if applicant already exists
    applicant = ScholarshipApplicant.objects.filter(email=email).first()
    if applicant:
        if not applicant.can_send_otp():
            language = form_data.get('language', 'sv')
            if language == 'en':
                err_msg = "OTP send limit exceeded. Please try again after 1 hour."
            else:
                err_msg = "Gränsen för att skicka engångskod har överskridits. Försök igen om 1 timme."
            raise ValidationError({"error": err_msg})

    application, _created = ScholarshipApplicant.objects.update_or_create(
        email=email,
        defaults={
            "form_data": form_data
        }
    )
    application.admin_verified = bool(SITE_CONFIG and not SITE_CONFIG.admin_check)
    application.email_verified = False
    
    application.generate_new_otp()
    send_otp_email(application, application.email)
    
    return Response({"msg": "your form is submitted"})


@api_view(['post'])
def send_verification_code(request, email):
    if email:
        email = str(email).strip().lower()
    application = ScholarshipApplicant.objects.filter(email=email).first()
    if not application:
        # Detect language from query param or request body (applicant doesn't exist yet)
        language = request.data.get('language') or request.query_params.get('language', 'sv')
        if language == 'en':
            err_msg = "We can't find any initiated applications linked to this email address. Please start a new one."
        else:
            err_msg = "Vi kan inte hitta någon påbörjad ansökan kopplad till denna e-postadress. Vänligen starta en ny ansökan."
        raise ValidationError({"error": err_msg})
    
    language = 'sv'
    if application.form_data and isinstance(application.form_data, dict):
        language = application.form_data.get('language', 'sv')

    if not application.can_send_otp():
        if language == 'en':
            err_msg = "OTP send limit exceeded. Please try again after 1 hour."
        else:
            err_msg = "Gränsen för att skicka engångskod har överskridits. Försök igen om 1 timme."
        raise ValidationError({"error": err_msg})

    application.generate_new_otp()
    send_otp_email(application, email)
    
    if language == 'en':
        msg = "A message with a verification code has been sent to your email."
    else:
        msg = "Ett meddelande med en verifieringskod har skickats till din e-post."
        
    return Response({"message": msg})


@api_view(['post'])
def verify_otp(request):
    from django.utils import timezone
    email = request.data.get('email')
    if email:
        email = str(email).strip().lower()
    otp = request.data.get('otp')

    if email is None:
        raise ValidationError({"error": "email is required"})

    if otp is None:
        raise ValidationError({"error": "otp is required"})
        
    application = get_object_or_404(ScholarshipApplicant, email=email)
    
    language = 'sv'
    if application.form_data and isinstance(application.form_data, dict):
        language = application.form_data.get('language', 'sv')

    # Check if locked out
    if application.is_otp_locked():
        if language == 'en':
            err_msg = "Too many failed attempts. Please try again later."
        else:
            err_msg = "För många misslyckade försök. Försök igen senare."
        raise ValidationError({"error": err_msg})

    # Check OTP expiration (10 min)
    if application.is_otp_expired():
        if language == 'en':
            err_msg = "OTP has expired. Please request a new one."
        else:
            err_msg = "Engångskoden (OTP) har gått ut. Vänligen begär en ny."
        raise ValidationError({"error": err_msg})

    if otp != application.otp:
        application.otp_failed_attempts += 1
        if application.otp_failed_attempts >= 5:
            application.otp_locked_until = timezone.now() + timezone.timedelta(minutes=15)
            application.save()
            if language == 'en':
                err_msg = "Too many failed attempts. You have been locked out for 15 minutes."
            else:
                err_msg = "För många misslyckade försök. Du har blivit spärrad i 15 minuter."
            raise ValidationError({"error": err_msg})
        
        application.save()
        if language == 'en':
            err_msg = f"Invalid OTP code. {5 - application.otp_failed_attempts} attempts remaining."
        else:
            err_msg = f"Ogiltig engångskod. {5 - application.otp_failed_attempts} försök återstår."
        raise ValidationError({"error": err_msg})

    application.email_verified = True
    application.refresh_otp()

    verify_token = jwt.encode({
            'email': application.email,
            "exp": datetime.datetime.now(datetime.UTC)\
                   +datetime.timedelta(minutes=30),
        },
        settings.SECRET_KEY,
        algorithm='HS256'
    )
    application.save()
    return Response({
        "application_token": verify_token
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
    if application.report_file:
        return Response({
            "success_count": application.success_count
        })

    location = application.form_data.get('municipality')
    language = application.form_data['language']

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


    # Get SiteConfig to retrieve custom prompts if they exist
    site_config = SiteConfig.objects.first()
    user_type = application.form_data['role']
    custom_system_prompt = None
    custom_rerank_prompt = None
    
    if site_config:
        if user_type.lower() == 'individual' or user_type.lower() == 'privatperson':
            custom_system_prompt = site_config.get_filter_prompt_individual()
            custom_rerank_prompt = site_config.get_reranker_prompt_individual()
        elif user_type.lower() == 'organisation' or user_type.lower() == 'organization':
            custom_system_prompt = site_config.get_filter_prompt_organization()
            custom_rerank_prompt = site_config.get_reranker_prompt_organization()
    
    report_data = stipo54.find_scholarships_v2(
        user_purpose=application.form_data['purpose_of_funding'],
        user_type=application.form_data['role'],
        municipality=application.form_data['municipality'],
        gender=application.form_data.get('gender'),
        language=application.form_data['language'],
        municipality_filter=application.form_data.get('include_municipality_filter', False),
        debug=False,  # Enable to see all filtering steps in terminal
        use_llm_rerank=True,
        custom_system_prompt=custom_system_prompt,
        custom_rerank_prompt=custom_rerank_prompt
    )

    # Format AI results - these are raw results from stipo54.find_scholarships_v2()
    formatted_ai_results = stipo54.format_scholarship_json(
        report_data,
        output_language=application.form_data['language']
    )

    # report_data = json.dumps(data)

    # report_data = json.loads(report_data)
    pdf_location = f"{str(uuid.uuid4())}.pdf"

    predefined = PreDefinedScholarship.objects.all()
    
    # Extract study level from form data
    study_level = application.form_data.get('study_level', '').lower()
    # Extract subject from education_level_option AND education_level_other (for "Annat"/Other case)
    education_level_option = application.form_data.get('education_level_option', [])
    education_level_other = application.form_data.get('education_level_other', '')
    subject = None
    
    # Map education_level_option to subject field values
    # Support both old format (economics, engineering, law) and new format
    # Include both regular selection and "Annat" (Other) field
    # Handle both list and string input formats
    education_parts = []
    if education_level_option:
        if isinstance(education_level_option, list):
            education_parts = education_level_option
        else:
            # If it's a string, wrap it in a list (don't use list() which converts to chars)
            education_parts = [str(education_level_option)]
    if education_level_other:
        education_parts.append(education_level_other)
    education_str = ' '.join(education_parts).lower()
    

    # Detect study level first — subject mapping depends on it
    study_level_lower = study_level.lower()
    if any(t in study_level_lower for t in [
        'undergraduate', 'bachelor', 'kandidat', 'kandidatnivå', 'grundnivå'
    ]):
        detected_level = 'undergraduate'
    elif any(t in study_level_lower for t in [
        'master', 'postgraduate', 'masternivå', 'magister'
    ]):
        detected_level = 'master'
    elif any(t in study_level_lower for t in [
        'phd', 'doctoral', 'doktorand', 'forskarutbildning',
        'doktorsexamen', 'licentiat'
    ]):
        detected_level = 'phd'
    else:
        detected_level = 'unknown'
        subject = None

    if detected_level == 'undergraduate':
        # Undergraduate subject mapping → undergraduate DB keys
        if _matches_any(education_str, ['law', 'political', 'juridik', 'legal', 'statsvetenskap']):
            subject = 'law_political'
        elif _matches_any(education_str, ['engineering', 'technology', 'teknik', 'ingenjörsvetenskap']):
            subject = 'engineering_technology'
        elif _matches_any(education_str, ['economics', 'business', 'ekonomi', 'administration', 'företagsekonomi', 'management']):
            subject = 'economics_business'
        elif _matches_any(education_str, ['medicine', 'health', 'medicin', 'hälsa', 'vårdutbildningar', 'vård']):
            subject = 'medicine_health'
        elif _matches_any(education_str, ['computer', 'it', 'data', 'datavetenskap', 'datalogi', 'datascience']):
            subject = 'cs_it_data'
        elif _matches_any(education_str, ['education', 'pedagogy', 'utbildning', 'pedagogik']):
            subject = 'education_pedagogy'
        elif _matches_any(education_str, ['psychology', 'behavioral', 'psykologi', 'beteendevetenskap']):
            subject = 'psychology_behavioral'
        elif _matches_any(education_str, ['environment', 'sustainability', 'miljö', 'hållbarhet']):
            subject = 'environment_sustainability'
        elif _matches_any(education_str, ['design', 'architecture', 'creative', 'arts', 'arkitektur', 'kreativa']):
            subject = 'design_architecture_arts'
        elif _matches_any(education_str, ['biology', 'chemistry', 'life science', 'biologi', 'kemi', 'naturvetenskap', 'livsvetenskap']):
            subject = 'biology_chemistry_life'

    elif detected_level == 'master':
        # Master's subject mapping → master DB keys (eng_tech_advanced etc.)
        if _matches_any(education_str, ['law', 'llm', 'legal', 'juridik']):
            subject = 'law_llm'
        elif _matches_any(education_str, ['public health', 'epidemiology', 'folkhälsa', 'epidemiologi', 'folkhälsovetenskap']):
            subject = 'public_health_epidemiology'
        elif _matches_any(education_str, ['engineering', 'technology', 'teknik', 'ingenjörsvetenskap', 'cybersecurity', 'supply chain', 'machine engineering']):
            subject = 'eng_tech_advanced'
        elif _matches_any(education_str, ['business', 'management', 'finance', 'accounting', 'international business', 'ekonomi', 'företagsekonomi']):
            subject = 'business_management'
        elif _matches_any(education_str, ['computer', 'digital business', 'data science', 'it', 'datalogi', 'datavetenskap']):
            subject = 'cs_digital_data_advanced'
        elif _matches_any(education_str, ['education', 'pedagogy', 'didactics', 'leadership', 'utbildning', 'pedagogik']):
            subject = 'education_didactics'
        elif _matches_any(education_str, ['environment', 'sustainability', 'urban planning', 'miljö', 'hållbarhet']):
            subject = 'environment_urban'
        elif _matches_any(education_str, ['life science', 'biotechnology', 'biotech', 'livsvetenskap', 'bioteknologi']):
            subject = 'life_science_biotech'
        elif _matches_any(education_str, ['design', 'architecture', 'creative', 'arts', 'arkitektur', 'kreativa']):
            subject = 'design_creative_advanced'
        elif _matches_any(education_str, ['social science', 'social work', 'psychology', 'political science', 'samhällsvetenskap', 'socialt', 'psykologi']):
            subject = 'social_sciences'

    elif detected_level == 'phd':
        # PhD subject mapping - only apply if user is individual
        # For individual PhD students, filter by subject
        is_individual = application.form_data['role'] and application.form_data['role'].lower() in ['individual', 'privatperson']
        
        if is_individual:
            # PhD subject mapping → phd DB keys
            if _matches_any(education_str, ['engineering', 'technology', 'teknik', 'ingenjörsvetenskap']):
                subject = 'phd_engineering_technology'
            elif _matches_any(education_str, ['economics', 'business', 'ekonomi', 'företagsekonomi']):
                subject = 'phd_economics'
            elif _matches_any(education_str, ['medicine', 'medicin', 'health', 'hälsa']):
                subject = 'phd_medicine'
            elif _matches_any(education_str, ['law', 'juridik', 'legal']):
                subject = 'phd_law'
            elif _matches_any(education_str, ['arts', 'culture', 'kultur', 'konst', 'creative', 'kreativa']):
                subject = 'phd_arts_culture'
            else:
                # If user selected something but no PhD match, only show "always" scholarships
                subject = None
        else:
            # For organization PhD applicants, no subject filtering
            subject = None


    # If user selected something but no match was found, only show "always" scholarships
    # This prevents irrelevant subject scholarships from appearing
    no_subject_match = (education_level_option or education_level_other) and subject is None
    
    # Use new study level filtering logic
    predefined_always, predefined_filtered = stipo54.get_predefined_scholarships_by_level(
        predefined,
        study_level=study_level,
        subject=subject,
        role=application.form_data['role'],
        sport=application.form_data.get('sport') if application.form_data['role'] == 'Organisation' else None,
        debug=True
    )
    
    # If no subject was matched but user selected something, ignore the filtered results
    if no_subject_match:
        predefined_filtered = predefined.none()
    
    if application.form_data['role'] == 'Organisation':
        # For organizations: start with subject-filtered results
        # Only override with sport filtering if a sport was actually selected
        sport_selected = application.form_data.get('sport', '')
        
        if sport_selected:
            # Organization selected a sport - filter by sport
            predefined_always = PreDefinedScholarship.objects.filter(sport__isnull=False, sport='always', is_organization=True)
            predefined = predefined.filter(sport__isnull=False, is_organization=True)
            
            if 'Football' in sport_selected or 'Fotboll' in sport_selected:
                predefined = predefined.filter(sport="football")
            elif 'Athletics' in sport_selected or 'Friidrott' in sport_selected:
                predefined = predefined.filter(sport="athletics")
            elif 'Golf' in sport_selected:
                predefined = predefined.filter(sport="golf")
            elif 'Gymnastics' in sport_selected or 'Gymnastik' in sport_selected:
                predefined = predefined.filter(sport="gymnastics")
            elif 'Floorball' in sport_selected or 'Innebandy' in sport_selected:
                predefined = predefined.filter(sport="floorball")
            elif 'Ice Hockey' in sport_selected or 'Ishockey' in sport_selected:
                predefined = predefined.filter(sport="ice_hockey")
            elif 'Swimming' in sport_selected or 'Simidrott' in sport_selected or 'Simning' in sport_selected:
                predefined = predefined.filter(sport="swimming")
            elif 'Handball' in sport_selected or 'Handboll' in sport_selected:
                predefined = predefined.filter(sport="handball")
            elif 'Equestrian' in sport_selected or 'Ridsport' in sport_selected:
                predefined = predefined.filter(sport="equestrian")
            elif 'Motorsports' in sport_selected or 'Motorsport' in sport_selected or 'Snowmobile' in sport_selected or 'Snöskoter' in sport_selected:
                predefined = predefined.filter(sport="motorsports")
            
            predefined_filtered = predefined
        else:
            # Organization did NOT select a sport - only show "always" scholarships for organizations
            # Do NOT show subject-filtered scholarships (those are for individuals)
            predefined_always = PreDefinedScholarship.objects.filter(is_organization=True, sport='always')
            predefined_filtered = PreDefinedScholarship.objects.none()  # No subject-specific scholarships for orgs without sport
        
        application.form_data['education_level_option'] = []
    else:
        # For individuals: use the filtered results from get_predefined_scholarships_by_level
        # Exclude "always" from the filtered set since it's handled separately
        pass

    # Combine AI results with predefined scholarships
    # Combine AI results with predefined scholarships using language-aware serializer
    output_language = application.form_data.get('language', 'en')
    predefined_scholarships_data = PreDefinedScholarshipSerializer(
        predefined_always, many=True, language=output_language
    ).data + PreDefinedScholarshipSerializer(
        predefined_filtered, many=True, language=output_language
    ).data
    
    # Translate predefined scholarships Purpose field to match output language
    predefined_scholarships_data = translate_predefined_scholarships(
        predefined_scholarships_data,
        output_language=output_language
    )
    
    # Order: Predefined scholarships FIRST (always subject + specific subject), then AI results
    # This ensures "always" scholarships appear first, then subject-specific, then AI-matched
    total_result = predefined_scholarships_data + formatted_ai_results[:10-len(predefined_scholarships_data)]
    
    # Clean all Unicode characters that cause black boxes in PDF
    total_result = clean_scholarship_data(total_result)

    # Clean form data before PDF (remove unwanted fields)
    cleaned_form_data = clean_profile_for_pdf(application.form_data)
    
    report_utils.create_pdf(
        total_result,
        cleaned_form_data,
        settings.WATERMARK_PATH,
        pdf_location
    )

    with open(pdf_location, 'rb') as file:
        application.report_file.save(application.email, File(file), save=True)

    application.success_count = len(total_result)
    application.pdf_created_at = datetime.datetime.now(datetime.UTC)
    application.save()
    os.remove(pdf_location)
    message = ""

    return Response({
        "success_count": len(total_result),
    })
def is_valid_domain(url):
    if not url:
        return False
    if not (url.startswith('http://') or url.startswith('https://')):
        return False
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        hostname = hostname.lower()
        
        # Build allowed domains from settings
        allowed_domains = {'localhost', '127.0.0.1'}
        
        # Add hostnames from ALLOWED_HOSTS
        for host in getattr(settings, 'ALLOWED_HOSTS', []):
            if host and host != '*':
                allowed_domains.add(host.lower())
                
        # Add hostnames from CORS_ALLOWED_ORIGINS
        for origin in getattr(settings, 'CORS_ALLOWED_ORIGINS', []):
            if origin:
                origin_parsed = urlparse(origin)
                if origin_parsed.hostname:
                    allowed_domains.add(origin_parsed.hostname.lower())
                    
        # Add hostnames from CSRF_TRUSTED_ORIGINS
        for origin in getattr(settings, 'CSRF_TRUSTED_ORIGINS', []):
            if origin:
                origin_parsed = urlparse(origin)
                if origin_parsed.hostname:
                    allowed_domains.add(origin_parsed.hostname.lower())

        return hostname in allowed_domains
    except Exception:
        return False


@api_view(['post'])
def generate_payment_link(request, email, method):
    # email = request.data.get('email')
    if method not in ['klarna', 'paypal', 'card']:
        raise ValidationError({"error": "invalid payment method."})
    coupon = request.data.get('coupon_code')
    discount = 0

    if coupon:
        if cpn:=Coupon.objects.filter(code=coupon).first():
            # Check if coupon is usable
            if not cpn.is_usable():
                raise ValidationError({"error": "this coupon is no longer available"})
            
            discount = cpn.discount
            
            # Track coupon usage
            import django.utils.timezone as tz
            cpn.times_used += 1
            cpn.last_used = tz.now()
            cpn.save()
        else:
            raise ValidationError({"error": "invalid coupon"})

    SITE_CONFIG = settings.SITE_CONFIG
    success_url = request.data.get('success_url')
    cancel_url = request.data.get('cancel_url')

    if not success_url:
        if settings.DEBUG:
            success_url = "http://localhost:3000/success"
        else:
            success_url = "https://app.stipendieportalen.se/success"

    if not cancel_url:
        if settings.DEBUG:
            cancel_url = "http://localhost:3000/success?error=payment failed"
        else:
            cancel_url = "https://app.stipendieportalen.se/success?error=payment failed"

    if not is_valid_domain(success_url):
        raise ValidationError({"error": "invalid success_url domain"})
    if not is_valid_domain(cancel_url):
        raise ValidationError({"error": "invalid cancel_url domain"})

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
    
    # Detect study level for accurate PhD pricing (handles Swedish terms like "Doktorsexamen")
    study_level = application.form_data.get('study_level', '').lower()
    if any(t in study_level for t in ['phd', 'doctoral', 'doktorand', 'forskarutbildning', 'doktorsexamen', 'licentiat']):
        detected_level = 'phd'
    else:
        detected_level = 'other'

    STD_PRICE = 299
    PHD_PRICE = 599
    ORG_PRICE = 1599

    # Check PhD FIRST (before general individual check) — use detected_level for accurate Swedish support
    if application.form_data.get('role', "").lower() in ['privatperson', 'individual'] and detected_level == 'phd':
        price = PHD_PRICE
    elif application.form_data.get('role', "").lower() in ['privatperson', 'individual']:
        price = STD_PRICE
    else:
        price = ORG_PRICE

    price = price - price*(discount/100)
    session = stripe.checkout.Session.create(
      success_url=success_url,
      cancel_url=cancel_url,
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

def verify_recaptcha_token(token):
    recaptcha_secret = getattr(settings, 'RECAPTCHA_SECRET_KEY', None)
    if not recaptcha_secret:
        return False, {"success": False, "error": "reCAPTCHA secret key is not configured in settings"}, 500

    try:
        import requests
        response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": recaptcha_secret,
                "response": token
            },
            timeout=10
        )
        result = response.json()
        if result.get("success"):
            return True, None, 200
        else:
            return False, {
                "success": False, 
                "error": "Captcha verification failed",
                "error-codes": result.get("error-codes", [])
            }, 400
    except Exception as e:
        return False, {
            "success": False,
            "error": f"Failed to verify captcha: {str(e)}"
        }, 500


@api_view(['post'])
def contact_us(request):
    name = request.data.get('name')
    email = request.data.get('email')
    message_body = request.data.get('message_body')
    token = request.data.get('token')

    if not name or not email or not message_body:
        raise ValidationError({"error": "name, email, and message_body are required"})

    if not token:
        raise ValidationError({"error": "reCAPTCHA token is required"})

    success, response_data, status_code = verify_recaptcha_token(token)
    if not success:
        return Response(response_data, status=status_code)

    subject = f"Contact Form Submission from {name}"
    message_text = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message_body}"

    send_mail(
        subject=subject,
        message=message_text,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=["kontakt@stipendieportalen.se"]
    )

    return Response({"message": "Message sent successfully"})


class VerifyCaptchaAPIView(APIView):
    @extend_schema(
        summary="Verify reCAPTCHA Token",
        description="Verifies the reCAPTCHA token against Google API. Requires active cookie consent when configured.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "token": {"type": "string", "example": "user_recaptcha_token"},
                    "consent_given": {"type": "boolean", "example": True}
                },
                "required": ["token"]
            }
        },
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({"success": False, "error": "Captcha token is required"}, status=400)

        # Check if site configuration requires cookie consent before reCAPTCHA verification
        site_config = SiteConfig.objects.first()
        if site_config and site_config.block_captcha_until_consent:
            consent_given = request.data.get('consent_given')
            if consent_given is False:
                return Response({
                    "success": False,
                    "error": "Cookie consent is required before verifying reCAPTCHA.",
                    "consent_required": True
                }, status=400)

        success, response_data, status_code = verify_recaptcha_token(token)
        if not success:
            return Response(response_data, status=status_code)

        return Response({"success": True, "message": "Captcha verified successfully"})


class CookieConsentAPIView(APIView):
    """
    Cookie Consent & reCAPTCHA Banner API Endpoint (Option 2)
    Provides status, configurations, and handles consent recording for blocking reCAPTCHA and form submissions.
    """

    @extend_schema(
        summary="Get Cookie Consent Banner Settings",
        description="Returns cookie consent configuration, reCAPTCHA blocking rules, and updated privacy policy info.",
        responses={200: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        site_config = SiteConfig.objects.first()
        keep_recaptcha = site_config.keep_recaptcha if site_config else True
        require_cookie_banner = site_config.require_cookie_banner if site_config else True
        block_captcha_until_consent = site_config.block_captcha_until_consent if site_config else True
        privacy_policy_url = site_config.privacy_policy_url if site_config else "/privacy-policy"

        return Response({
            "keep_recaptcha": keep_recaptcha,
            "require_cookie_banner": require_cookie_banner,
            "block_captcha_until_consent": block_captcha_until_consent,
            "privacy_policy_updated": True,
            "privacy_policy_url": privacy_policy_url,
            "message": "reCAPTCHA requires active cookie consent before initialization and form submission." if block_captcha_until_consent else "Cookie consent is optional."
        }, status=200)

    @extend_schema(
        summary="Submit Cookie & reCAPTCHA Consent Preference",
        description="Records visitor consent preference. Unblocks reCAPTCHA script loading and form submission when consent_given is true.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "consent_given": {"type": "boolean", "example": True},
                    "consent_type": {"type": "string", "example": "all"}
                },
                "required": ["consent_given"]
            }
        },
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        consent_given = request.data.get('consent_given')
        if consent_given is None:
            return Response({
                "success": False,
                "error": "consent_given (boolean) is required"
            }, status=400)

        consent_given = bool(consent_given)
        consent_type = str(request.data.get('consent_type', 'all'))

        # Extract visitor IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            user_ip = x_forwarded_for.split(',')[0].strip()
        else:
            user_ip = request.META.get('REMOTE_ADDR')

        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Log cookie consent choice
        try:
            CookieConsentLog.objects.create(
                user_ip=user_ip,
                consent_given=consent_given,
                consent_type=consent_type,
                user_agent=user_agent
            )
        except Exception:
            pass

        site_config = SiteConfig.objects.first()
        privacy_policy_url = site_config.privacy_policy_url if site_config else "/privacy-policy"

        if consent_given:
            return Response({
                "success": True,
                "consent_given": True,
                "captcha_unblocked": True,
                "privacy_policy_url": privacy_policy_url,
                "message": "Cookie consent recorded successfully. reCAPTCHA and form submission are now unblocked."
            }, status=200)
        else:
            return Response({
                "success": False,
                "consent_given": False,
                "captcha_unblocked": False,
                "privacy_policy_url": privacy_policy_url,
                "message": "Cookie consent declined. reCAPTCHA and form submission remain blocked."
            }, status=200)







