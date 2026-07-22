import os as _os

from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.conf import settings

from .models import ScholarshipApplicant, SiteConfig, EmailTemplate
from app.embed1 import update_pinecone_embeddings


@receiver(post_save, sender=ScholarshipApplicant)
def handle_application_save(sender, instance, created, **kwargs):
    """
    After all conditions are met (admin_verified, email_verified, paid, report_file exists):
      1. Read the PDF from disk and email it to the customer.
      2. Delete the physical PDF file from disk immediately — no second copy retained.
      3. Clear the report_file field in the DB — keeping form_data and success_count.

    The DB record is intentionally preserved so form input data and scholarship
    results remain queryable. Only the PDF binary is discarded.
    """
    if instance.admin_verified and instance.report_file \
            and instance.email_verified and instance.paid:

        pdf_path = instance.report_file.path

        # --- 1. Build and send the email ---
        language = 'sv'
        if instance.form_data and isinstance(instance.form_data, dict):
            language = instance.form_data.get('language', 'sv')

        try:
            email_template = EmailTemplate.objects.first()
        except Exception:
            email_template = None

        if email_template:
            if language == 'en':
                subject = email_template.report_subject_en
                body_template = email_template.report_body_en
            else:
                subject = email_template.report_subject_sv
                body_template = email_template.report_body_sv
        else:
            if language == 'en':
                subject = "Your scholarship report is ready"
                body_template = "Hello,\n\nYour scholarship report is attached. Please review the attached file for the matching scholarships.\n\nReport file: {report_file_name}\n\nBest regards,\nScholarship team"
            else:
                subject = "Din stipendierapport är klar"
                body_template = "Hej,\n\nDin stipendierapport är bifogad. Granska den bifogade filen för matchade stipendier.\n\nRapportfil: {report_file_name}\n\nVänliga hälsningar,\nStipendieteamet"

        report_file_name = _os.path.basename(instance.report_file.name)
        plain_body = body_template.replace('{report_file_name}', report_file_name)
        plain_body_html = plain_body.replace('\n', '<br>')

        # Format HTML body for modern display
        html_body = f"""
        <div style="font-family: Arial, sans-serif; padding: 25px; max-width: 600px; margin: 0 auto; line-height: 1.6; color: #333; border: 1px solid #e8eaed; border-radius: 12px; background-color: #ffffff;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: #1a73e8; margin: 0;">{subject}</h2>
            </div>
            <div style="font-size: 16px; color: #444;">
                {plain_body_html}
            </div>
        </div>
        """

        email_msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_body,
            from_email=settings.EMAIL_HOST_USER,
            to=[instance.email],
        )
        email_msg.attach_alternative(html_body, "text/html")

        with open(pdf_path, "rb") as pdf:
            email_msg.attach(report_file_name, pdf.read(), "application/pdf")

        print("SENDING FILE>>>")
        email_msg.send()
        print(f"PDF emailed to {instance.email}")

        # --- 2. Delete the physical file from disk immediately ---
        try:
            _os.remove(pdf_path)
            print(f"Physical PDF deleted: {pdf_path}")
        except OSError as exc:
            print(f"Could not delete physical PDF ({pdf_path}): {exc}")

        # --- 3. Clear report_file field in DB (keep the record with form_data) ---
        # Use .update() to avoid re-triggering this post_save signal.
        ScholarshipApplicant.objects.filter(pk=instance.pk).update(
            report_file="",
            pdf_created_at=None,
        )
        print(f"report_file cleared for {instance.email} — form_data and results retained.")


from threading import Thread
from django.db.models import F

from django.db.models.signals import pre_save

@receiver(pre_save, sender=SiteConfig)
def handle_site_config_pre_save(sender, instance, **kwargs):
    try:
        old_instance = SiteConfig.objects.get(pk=instance.pk)
        instance._old_file_name = old_instance.scholarships_db_file.name if old_instance.scholarships_db_file else None
        instance._old_index = old_instance.get_active_dataset_index_name()
        instance._old_pinecone_updated = old_instance.pinecone_updated
    except SiteConfig.DoesNotExist:
        instance._old_file_name = None
        instance._old_index = None
        instance._old_pinecone_updated = False

@receiver(post_save, sender=SiteConfig)
def handle_site_config_save(sender, instance, created, **kwargs):
    settings.SITE_CONFIG = instance

    # Skip if this is an internal status update (to prevent recursive signals)
    if kwargs.get('update_fields') and len(kwargs.get('update_fields', [])) <= 2:
        if 'upload_in_progress' in kwargs.get('update_fields', []) or 'pinecone_updated' in kwargs.get('update_fields', []):
            return

    try:
        current_file = instance.scholarships_db_file
        current_index = instance.get_active_dataset_index_name()
        previous_index = getattr(instance, '_old_index', instance.last_active_dataset_index)
        
        # Check if file changed or a new file was uploaded
        old_file_name = getattr(instance, '_old_file_name', None)
        new_file_name = current_file.name if current_file else None
        
        # Detect new upload or file change:
        # 1. Uncommitted file in FileField (means a new file was uploaded in current save)
        # 2. File name changed
        file_changed = False
        if current_file:
            if hasattr(current_file, '_committed') and not current_file._committed:
                file_changed = True
            elif new_file_name != old_file_name:
                file_changed = True
        
        print(f"\n{'='*60}")
        print(f"📋 SiteConfig Saved")
        print(f"{'='*60}")
        print(f"  📍 Current Active Index: {current_index}")
        print(f"  📁 File: {new_file_name if new_file_name else 'No file'}")
        print(f"  📁 Old File: {old_file_name if old_file_name else 'No old file'}")
        print(f"  🔄 File Changed: {file_changed}")
        print(f"  ⏳ Upload Status: {'IN PROGRESS' if instance.upload_in_progress else 'Ready'}")
        
        # Prevent duplicate uploads if one is already running
        if instance.upload_in_progress:
            print(f"  ⚠️  Upload already in progress - skipping duplicate upload")
            print(f"{'='*60}\n")
            return
        
        # Only trigger upload if we have a file AND a meaningful dataset change occurred:
        # 1. The index name changed (user switched datasets)
        # 2. The file was actually changed
        # 3. Initial save with file
        index_changed = current_index != previous_index
        dataset_changed = index_changed or file_changed or created
        
        if not current_file:
            print(f"  ℹ️  No file attached - skipping upload")
            if index_changed:
                SiteConfig.objects.filter(id=instance.id).update(last_active_dataset_index=current_index)
                print(f"  ✅ Index tracking updated: {current_index}")
            print(f"{'='*60}\n")
            return
        
        # File exists - check if we should upload
        should_upload = False
        reason = ""
        
        if index_changed:
            should_upload = True
            reason = f"Index switched: '{previous_index}' → '{current_index}'"
        elif file_changed:
            should_upload = True
            reason = f"New Excel file uploaded"
        elif created:
            should_upload = True
            reason = "Initial configuration created with file"
        
        if should_upload:
            print(f"  ✅ UPLOAD TRIGGERED")
            print(f"  Reason: {reason}")
            print(f"  🎯 Target Index: {current_index}")
            print(f"  Status: Starting background upload...")
            print(f"{'='*60}\n")
            
            # Use direct database update to avoid recursive signal triggering
            SiteConfig.objects.filter(id=instance.id).update(
                upload_in_progress=True,
                pinecone_updated=False,
                last_active_dataset_index=current_index
            )
            
            # Start upload in a background thread so shutdown is not blocked
            thread = Thread(
                target=_upload_with_status_update,
                args=(current_file.path, current_index, instance.id)
            )
            thread.daemon = True
            thread.start()
        else:
            print(f"  ℹ️  No upload needed (no meaningful dataset change detected)")
            print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error in SiteConfig signal: {e}")
        print(f"{'='*60}\n")
        raise e


def _upload_with_status_update(file_path, index_name, config_id):
    """Upload to Pinecone and update SiteConfig status when done"""
    try:
        update_pinecone_embeddings(file_path, index_name)
        
        # Use direct database update to avoid triggering signal again
        SiteConfig.objects.filter(id=config_id).update(
            upload_in_progress=False,
            pinecone_updated=True
        )
        
        print(f"\n{'='*60}")
        print(f"✅ UPLOAD COMPLETE!")
        print(f"{'='*60}")
        print(f"  🎯 Index: {index_name}")
        print(f"  📊 Status: Ready to query")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        print(f"{'='*60}\n")
        # Use direct database update to avoid triggering signal
        try:
            SiteConfig.objects.filter(id=config_id).update(
                upload_in_progress=False,
                pinecone_updated=False
            )
        except Exception:
            pass






 
