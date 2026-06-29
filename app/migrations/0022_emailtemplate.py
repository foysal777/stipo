from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0021_fix_charfield_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('otp_subject_en', models.CharField(default='Your scholarship OTP code', max_length=255, verbose_name='OTP Email Subject (EN)')),
                ('otp_body_en', models.TextField(default='Hello,\n\nUse this OTP code to continue your scholarship search:\n\n{otp}\n\nThank you.', help_text='Use {otp} to insert the one time passcode.', verbose_name='OTP Email Body (EN)')),
                ('otp_subject_sv', models.CharField(default='Din OTP-kod för stipendiesökning', max_length=255, verbose_name='OTP Email Subject (SV)')),
                ('otp_body_sv', models.TextField(default='Hej,\n\nAnvänd denna OTP-kod för att fortsätta din stipendiesökning:\n\n{otp}\n\nTack.', help_text='Use {otp} to insert the one time passcode.', verbose_name='OTP Email Body (SV)')),
                ('report_subject_en', models.CharField(default='Your scholarship report is ready', max_length=255, verbose_name='Report Email Subject (EN)')),
                ('report_body_en', models.TextField(default='Hello,\n\nYour scholarship report is attached. Please review the attached file for the matching scholarships.\n\nReport file: {report_file_name}\n\nBest regards,\nScholarship team', help_text='Use {report_file_name} to insert the attached report file name.', verbose_name='Report Email Body (EN)')),
                ('report_subject_sv', models.CharField(default='Din stipendierapport är klar', max_length=255, verbose_name='Report Email Subject (SV)')),
                ('report_body_sv', models.TextField(default='Hej,\n\nDin stipendierapport är bifogad. Granska den bifogade filen för matchade stipendier.\n\nRapportfil: {report_file_name}\n\nVänliga hälsningar,\nStipendieteamet', help_text='Use {report_file_name} to insert the attached report file name.', verbose_name='Report Email Body (SV)')),
            ],
            options={
                'verbose_name': 'Email Template',
                'verbose_name_plural': 'Email Templates',
            },
        ),
    ]
