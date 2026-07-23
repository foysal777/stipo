from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0026_cleanup_predefinedscholarship_sv'),
    ]

    operations = [
        migrations.CreateModel(
            name='CookieConsentLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('consent_given', models.BooleanField(default=False)),
                ('consent_type', models.CharField(default='all', help_text='e.g. all, recaptcha, necessary', max_length=50)),
                ('user_agent', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Cookie Consent Log',
                'verbose_name_plural': 'Cookie Consent Logs',
            },
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='block_captcha_until_consent',
            field=models.BooleanField(default=True, help_text='Block reCAPTCHA script loading and form submit action until visitor actively consents to cookies', verbose_name='Block reCAPTCHA Until Consent'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='keep_recaptcha',
            field=models.BooleanField(default=True, help_text='Keep reCAPTCHA enabled for security', verbose_name='Keep reCAPTCHA'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='privacy_policy_url',
            field=models.CharField(default='/privacy-policy', help_text='URL path or full URL to updated privacy policy', max_length=255, verbose_name='Privacy Policy URL'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='require_cookie_banner',
            field=models.BooleanField(default=True, help_text='Show cookie consent banner before reCAPTCHA and form submission', verbose_name='Require Cookie/Consent Banner'),
        ),
    ]
