#server code 

from django.contrib import admin
from django.urls import reverse
from django.shortcuts import redirect
from django.db import models
 
# admin.py
from django.contrib import admin
from .models import (
    SiteConfig, DatasetUpload, FAQ, ScholarshipApplicant,
    Review, Coupon, PreDefinedScholarship, EmailTemplate
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

    fieldsets = (
        ('System Settings', {
            'fields': ('admin_check',),
            'description': 'Basic system configuration'
        }),
        ('Custom LLM Filter Prompt - Individual Users', {
            'fields': ('use_default_query_filter_individual', 'custom_query_prompt_individual',),
            'description': 'Override the default LLM filter prompt for individual users. Check "Use Default" to use hardcoded default, or uncheck to use custom prompt.',
            'classes': ('collapse',)
        }),
        ('Custom LLM Filter Prompt - Organization Users', {
            'fields': ('use_default_query_filter_organization', 'custom_query_prompt_organization',),
            'description': 'Override the default LLM filter prompt for organization users - förening, klubb, juridisk person. Check "Use Default" to use hardcoded default, or uncheck to use custom prompt.',
            'classes': ('collapse',)
        }),
        ('Custom LLM Reranker Prompt - Individual Users', {
            'fields': ('use_default_reranker_individual', 'custom_reranker_prompt_individual',),
            'description': 'Override the default LLM reranker prompt for individual users. Check "Use Default" to use hardcoded default, or uncheck to use custom prompt.',
            'classes': ('collapse',)
        }),
        ('Custom LLM Reranker Prompt - Organization Users', {
            'fields': ('use_default_reranker_organization', 'custom_reranker_prompt_organization',),
            'description': 'Override the default LLM reranker prompt for organization users. Check "Use Default" to use hardcoded default, or uncheck to use custom prompt.',
            'classes': ('collapse',)
        }),
    )
 
 
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
    list_display = ('code', 'discount', 'times_used', 'max_uses', 'is_active', 'last_used', 'usage_percentage')
    list_filter = ('is_active', 'created_at', 'last_used')
    search_fields = ('code',)
    readonly_fields = ('code', 'times_used', 'created_at', 'last_used', 'usage_percentage', 'is_usable_status')
   
    fieldsets = (
        ('Coupon Info', {
            'fields': ('code', 'discount', 'is_active')
        }),
        ('Usage Limits', {
            'fields': ('max_uses', 'times_used', 'usage_percentage')
        }),
        ('Tracking', {
            'fields': ('created_at', 'last_used', 'is_usable_status')
        }),
    )
   
    def usage_percentage(self, obj):
        """Display coupon usage percentage"""
        if obj.max_uses is None:
            return "Unlimited"
        if obj.max_uses == 0:
            return "0%"
        percentage = (obj.times_used / obj.max_uses) * 100
        return f"{percentage:.1f}% ({obj.times_used}/{obj.max_uses})"
    usage_percentage.short_description = "Usage"
   
    def is_usable_status(self, obj):
        """Show if coupon is still usable"""
        if obj.is_usable():
            return "✅ Active & Usable"
        elif not obj.is_active:
            return "🔴 Disabled"
        elif obj.max_uses and obj.times_used >= obj.max_uses:
            return f"🛑 Limit Reached ({obj.times_used}/{obj.max_uses})"
        return "⚠️ Unavailable"
    is_usable_status.short_description = "Status"
 

@admin.register(DatasetUpload)
class DatasetUploadAdmin(admin.ModelAdmin):
    list_display = (
        'dataset_index_name', 'use_default_dataset', 'pinecone_updated',
        'upload_status', 'upload_progress', 'rows_uploaded',
        'total_rows', 'last_uploaded_at'
    )
    readonly_fields = (
        'pinecone_updated', 'upload_in_progress', 'upload_status',
        'upload_progress', 'rows_uploaded', 'total_rows',
        'upload_error_message', 'last_uploaded_at', 'created_at',
        'updated_at'
    )
    fieldsets = (
        ('Dataset Upload', {
            'fields': (
                'scholarships_db_file',
                'use_default_dataset',
                'dataset_index_name',
            ),
            'description': 'Upload a dataset file and choose the Pinecone index name used for queries.',
        }),
        ('Upload Status', {
            'fields': (
                'pinecone_updated',
                'upload_in_progress',
                'upload_status',
                'upload_progress',
                'rows_uploaded',
                'total_rows',
                'upload_error_message',
                'last_uploaded_at',
            ),
            'description': 'High-level status of the dataset upload to Pinecone. Status fields are read-only and updated during background upload.',
        }),
        ('Timing', {
            'fields': ('created_at', 'updated_at',),
            'classes': ('collapse',),
        }),
    )
    search_fields = ('dataset_index_name',)
    list_filter = ('use_default_dataset', 'pinecone_updated', 'upload_status')

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return self.readonly_fields
        return self.readonly_fields


@admin.register(PreDefinedScholarship)
class PreDefinedScholarshipAdmin(admin.ModelAdmin):
    list_display = [
        'organization_name'
    ]
 
    search_fields = ['subject']
    pass


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not EmailTemplate.objects.exists()
 
    def changelist_view(self, request, extra_context=None):
        obj = EmailTemplate.objects.first()
        if obj:
            url = reverse(
                'admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name),
                args=[obj.pk]
            )
            return redirect(url)
        app_label = EmailTemplate._meta.app_label
        model_name = EmailTemplate._meta.model_name
        return redirect(reverse(f'admin:{app_label}_{model_name}_add'))

    fieldsets = (
        ('Email Templates - OTP', {
            'fields': ('otp_subject_en', 'otp_body_en', 'otp_subject_sv', 'otp_body_sv'),
            'description': 'OTP email templates for English and Swedish. Use {otp} in the body text.'
        }),
        ('Email Templates - Final Report', {
            'fields': ('report_subject_en', 'report_body_en', 'report_subject_sv', 'report_body_sv'),
            'description': 'Final report email templates for English and Swedish. Use {report_file_name} in the body text.'
        }),
    )
