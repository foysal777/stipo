from django.conf import settings
from django.db import models

import random
import uuid


def create_otp(length: int = 4):
    return ''.join(random.choices('0123456789', k=length))

def generate_pdf_path(instance, file_name):
    return f"report-{str(uuid.uuid4())}.pdf"

class ScholarshipApplicant(models.Model):
    email = models.EmailField(unique=True)

    form_data = models.JSONField(default=dict)

    paid = models.BooleanField(default=False) 
    email_verified = models.BooleanField(default=False)
    admin_verified = models.BooleanField(default=False)
    report_file = models.FileField(upload_to=generate_pdf_path, null=True)
    otp = models.CharField(default=create_otp)
    success_count = models.PositiveIntegerField(default=0)

    def refresh_otp(self):
        self.otp = create_otp()

    def __str__(self):
        return f"{self.email}"

def scholarship_db_path(instance, filename):
    return "new_scholarships_db.xlsx"

class SiteConfig(models.Model):
    # process_charge = models.DecimalField(
    #     max_digits=5, decimal_places=2,
    #     default=0
    # )

    admin_check = models.BooleanField(default=True)
    scholarships_db_file = models.FileField(upload_to=scholarship_db_path, null=True)
    pinecone_updated = models.BooleanField(default=False)

    query_template = models.TextField(default="")
    use_default = models.BooleanField(default=True)
    def __str__(self):
        return "Site Settings"
    pass


class FAQ(models.Model):

    question = models.TextField()
    answer = models.TextField()

    question_sv = models.TextField(default="")
    answer_sv = models.TextField(default="")

    def __str__(self):
        return self.question[:50] + ('...' if len(self.question) > 50 else '')

class Review(models.Model):
    email = models.EmailField()
    description = models.TextField()
    stars = models.SmallIntegerField()

import random
import string

def random_string():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(7))


class Coupon(models.Model):
    discount = models.PositiveIntegerField(default=0)
    code = models.CharField(max_length=7, default=random_string, blank=True, null=True)
# class Database(models.Model):


SPORT_CHOICES = [
    ('always', 'always'),
    ("football","football",),
    ("athletics","athletics",),
    ("golf","golf",),
    ("gymnastics","gymnastics",),
    ("floorball","floorball",),
    ("ice_hockey","ice_hockey",),
    ("swimming","swimming", ),
    ("handball","handball", ),
    ("equestrian","equestrian", ),
    ("motorsports","motorsports", ),
]

class PreDefinedScholarship(models.Model):
    is_organization = models.BooleanField(default=True)
    sport = models.CharField(
        max_length=50,
        choices=SPORT_CHOICES,
        blank=True,
        null=True
    )

    subject = models.CharField(null=True, blank=True, choices=[
        # educationLevels
        ("always", "always"),
        # ("primarySchool", "primarySchool"),
        # ("secondarySchool", "secondarySchool"),
        # ("postSecondary", "postSecondary"),
        # ("university", "university"),
        # ("master", "master"),
        # ("phd", "phd"),

        # upperSecondary
        ("socialSciences", "socialSciences"),
        ("economics", "economics"),
        ("naturalSciences", "naturalSciences"),
        ("technology", "technology"),
        ("arts", "arts"),
        ("electricityEnergy", "electricityEnergy"),
        ("vehicleTransport", "vehicleTransport"),
        ("construction", "construction"),
        ("salesService", "salesService"),
        ("childRecreation", "childRecreation"),
        ("other", "other"),

        # universityPrograms
        ("engineering", "engineering"),
        ("medicine", "medicine"),
        ("cs", "cs"),
        ("education", "education"),
        ("psychology", "psychology"),
        ("law", "law"),
        ("environment", "environment"),
        ("design", "design"),
        ("biology", "biology"),

        # masterPrograms
        ("publicHealth", "publicHealth"),
        ("engineering", "engineering"),
        ("business", "business"),
        ("cs", "cs"),
        ("education", "education"),
        ("environment", "environment"),
        ("lifeScience", "lifeScience"),
        ("law", "law"),
        ("design", "design"),
        ("socialSciences", "socialSciences"),

        # postSecondaryPrograms
        ("pharmacyTech", "pharmacyTech"),
        ("ambulance", "ambulance"),
        ("animalCare", "animalCare"),
        ("softwareDev", "softwareDev"),
        ("trainDriver", "trainDriver"),
        ("dentalNurse", "dentalNurse"),
        ("medicalAdmin", "medicalAdmin"),
        ("accounting", "accounting"),
        ("childcare", "childcare"),
        ("sport", "sport"),
    ])

    # study_level = models.CharField(choices=[
    #     ("universityUndergraduate", "universityUndergraduate"),
    #     ("universityMasters", "universityMasters"),
    #     ("postSecondary", "postSecondary"),
    #     ("upperSecondary", "upperSecondary"),
    #     ("compulsory", "compulsory"),
    #     ("phd", "phd"),
    # ])

    organization_name = models.TextField()
    munucipality = models.TextField()
    category = models.TextField()
    purpose = models.TextField()
    organization_email = models.TextField()
    organization_website = models.TextField()
    organization_phone = models.TextField()
    organization_assets = models.TextField()
    organization_main_address = models.TextField()
    organization_postal_code = models.TextField()
    organization_city = models.TextField()
    organization_county = models.TextField()


class PreDefinedScholarship_Sv(models.Model):
    subject = models.CharField(choices=(
    
    ))
    study_level = models.CharField(choices=(
        
    ))
    organization_name = models.TextField()
    munucipality = models.TextField()
    category = models.TextField()
    purpose = models.TextField()
    organization_email = models.TextField()
    organization_website = models.TextField()
    organization_phone = models.TextField()
    organization_assets = models.TextField()
    organization_main_address = models.TextField()
    organization_postal_code = models.TextField()
    organization_city = models.TextField()
    organization_county = models.TextField()
    
    # "Name": "Namn",
    # "Municipality": "Kommun",
    # "Category": "Kategori",
    # "Purpose": "Ändamål",
    # "Study Level": "Studienivå",
    # "Email": "E-post",
    # "Website": "Websida",
    # "Phone": "Telefon",
    # "Assets": "Tillgångar",
    # "Main Address": "Huvudadress",
    # "Postal Code": "Postnummer",
    # "City": "Postort",
    # "County": "Län",