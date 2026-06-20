from django.contrib import admin
from django.urls import reverse
from django.shortcuts import redirect
from django.db import models

# admin.py
from django.contrib import admin
from .models import (
    SiteConfig, FAQ, ScholarshipApplicant,
    Review, Coupon, PreDefinedScholarship
)


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()

    def changelist_view(self, request, extra_context=None):
        obj = SiteConfig.objects.first()
        if obj:
            url = reverse(
                'admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name),
                args=[obj.pk]
            )
            return redirect(url)
        app_label = SiteConfig._meta.app_label
        model_name = SiteConfig._meta.model_name
        print(app_label, model_name)
        return redirect(reverse(f'admin:{app_label}_{model_name}_add'))
        return super().changelist_view(request, extra_context)

    def get_readonly_fields(self, request, v):
        return ["pinecone_updated"]


@admin.register(FAQ)
class FAQ_Admin(admin.ModelAdmin):
	pass


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    pass


@admin.register(ScholarshipApplicant)
class ScholarshipApplicant(admin.ModelAdmin):
    # def has_add_permission(self, request):
    #     return False

    def get_readonly_fields(self, request, obj=None):
        flag = True
        if obj is None:
            return []
        return [
            field.name for field in obj._meta.fields
            if field.name not in ['admin_verified', 'paid', 'form_data']
        ]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [
            "code"
        ]


@admin.register(PreDefinedScholarship)
class PreDefinedScholarshipAdmin(admin.ModelAdmin):
    list_display = [
        'organization_name'
    ]

    search_fields = ['subject']
    pass