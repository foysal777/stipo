from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0023_populate_email_templates'),
    ]

    operations = [
        migrations.AddField(
            model_name='scholarshipapplicant',
            name='otp_created_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='scholarshipapplicant',
            name='otp_send_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
