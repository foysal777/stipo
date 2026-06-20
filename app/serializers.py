from rest_framework import serializers

from .models import ScholarshipApplicant, Review, PreDefinedScholarship


# class ScholarshipApplicantSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ScholarshipApplicant
#         fields = [
#             'id',
#             'role',
#             'name',
#             'email',
#             'gender',
#             'age',
#             'study_level',
#             'elite_athlete',
#             'municipality',
#         ]

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'


class PreDefinedScholarshipSerializer(serializers.ModelSerializer):
    Namn = serializers.SerializerMethodField()
    Name = serializers.SerializerMethodField()
    Municipality = serializers.SerializerMethodField()
    Category = serializers.SerializerMethodField()
    Purpose = serializers.SerializerMethodField()
    StudyUtbildningsnivå = serializers.SerializerMethodField()
    Email = serializers.SerializerMethodField()
    Website = serializers.SerializerMethodField()
    Phone = serializers.SerializerMethodField()
    Assets = serializers.SerializerMethodField()
    MainHuvudadress = serializers.SerializerMethodField()
    PostalPostnr = serializers.SerializerMethodField()
    City = serializers.SerializerMethodField()
    County = serializers.SerializerMethodField()
    Sportkategori = serializers.SerializerMethodField()
    Sport = serializers.SerializerMethodField()

    class Meta:
        model = PreDefinedScholarship
        fields = [
            'Namn', 'Municipality', "Category", "Purpose",
            "StudyUtbildningsnivå", "Email", "Website", "Phone",
            "Assets", "MainHuvudadress", "PostalPostnr", "City",
            "County", "Sportkategori", "Name", "Sport", 'id'
        ]

    def get_Namn(self, instance):
        return instance.organization_name

    def get_Name(self, instance):
        return instance.organization_name

    def get_Municipality(self, instance):
        return instance.munucipality

    def get_Category(self, instance):
        return instance.category

    def get_Purpose(self, instance):
        return instance.purpose

    def get_StudyUtbildningsnivå(self, instance):
        return instance.subject

    def get_Email(self, instance):
        return instance.organization_email

    def get_Website(self, instance):
        return instance.organization_website

    def get_Phone(self, instance):
        return instance.organization_phone

    def get_Assets(self, instance):
        return instance.organization_assets

    def get_MainHuvudadress(self, instance):
        return instance.organization_main_address

    def get_PostalPostnr(self, instance):
        return instance.organization_postal_code

    def get_City(self, instance):
        return instance.organization_city

    def get_County(self, instance):
        return instance.organization_county

    def get_Sportkategori(self, instance):
        return None  # No corresponding field on the model

    def get_Sport(self, instance):
        return instance.sport  # No corresponding field on the model


class MockSerializer(serializers.ModelSerializer):
    Name = serializers.SerializerMethodField()
    Subject = serializers.SerializerMethodField()
    Municipality = serializers.SerializerMethodField()
    Category = serializers.SerializerMethodField()
    Purpose = serializers.SerializerMethodField()
    Email = serializers.SerializerMethodField()
    Website = serializers.SerializerMethodField()
    Phone = serializers.SerializerMethodField()
    Assets = serializers.SerializerMethodField()
    Main_Address = serializers.SerializerMethodField()
    Postal = serializers.SerializerMethodField()
    City = serializers.SerializerMethodField()
    County = serializers.SerializerMethodField()
    Sport = serializers.SerializerMethodField()


    class Meta:
        model = PreDefinedScholarship
        fields = [
            'Name', 'Municipality', "Category", "Purpose",
            "Subject", "County",
            "Email", "Website", "Phone",
            "Assets", "City", "Postal",
            "Sport", 'id', "Main_Address",
        ]

    def get_Name(self, instance):
        return instance.organization_name

    def get_Municipality(self, instance):
        return instance.munucipality

    def get_Category(self, instance):
        return instance.category

    def get_Purpose(self, instance):
        return instance.purpose

    def get_Email(self, instance):
        return instance.organization_email

    def get_Website(self, instance):
        return instance.organization_website

    def get_Phone(self, instance):
        return instance.organization_phone

    def get_Assets(self, instance):
        return instance.organization_assets


    def get_City(self, instance):
        return instance.organization_city

    def get_County(self, instance):
        return instance.organization_county

    def get_Sport(self, instance):
        return instance.sport  # No corresponding field on the model

    def get_Main_Address(self, instance):
        return instance.organization_main_address  # No corresponding field on the model


    def get_Postal(self, instance):
        return instance.organization_postal_code  # No corresponding field on the model

    def get_Subject(self, instance):
        return instance.subject  # No corresponding field on the model

PreDefinedScholarshipSerializer = MockSerializer