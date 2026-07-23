from django.db import migrations

def create_default_email_template(apps, schema_editor):
    EmailTemplate = apps.get_model('app', 'EmailTemplate')
    if not EmailTemplate.objects.exists():
        EmailTemplate.objects.create(
            otp_subject_en="Your scholarship OTP code",
            otp_body_en="Hello,\n\nUse this OTP code to continue your scholarship search:\n\n{otp}\n\nThank you.",
            otp_subject_sv="Din OTP-kod för stipendiesökning",
            otp_body_sv="Hej,\n\nAnvänd denna OTP-kod för att fortsätta din stipendiesökning:\n\n{otp}\n\nTack.",
            report_subject_en="Your scholarship report is ready",
            report_body_en="Hello,\n\nYour scholarship report is attached. Please review the attached file for the matching scholarships.\n\nReport file: {report_file_name}\n\nBest regards,\nScholarship team",
            report_subject_sv="Din stipendierapport är klar",
            report_body_sv="Hej,\n\nDin stipendierapport är bifogad. Granska den bifogade filen för matchade stipendier.\n\nRapportfil: {report_file_name}\n\nVänliga hälsningar,\nStipendieteamet"
        )

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0022_emailtemplate'),
    ]

    operations = [
        migrations.RunPython(create_default_email_template),
    ]
