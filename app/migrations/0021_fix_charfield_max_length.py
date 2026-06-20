from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0020_alter_predefinedscholarship_sport'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scholarshipapplicant',
            name='otp',
            field=models.CharField(default='0000', max_length=6),
        ),
        migrations.AlterField(
            model_name='predefinedscholarship',
            name='subject',
            field=models.CharField(
                blank=True,
                max_length=50,
                null=True,
                choices=[
                    ('always', 'always'),
                    ('socialSciences', 'socialSciences'),
                    ('economics', 'economics'),
                    ('naturalSciences', 'naturalSciences'),
                    ('technology', 'technology'),
                    ('arts', 'arts'),
                    ('electricityEnergy', 'electricityEnergy'),
                    ('vehicleTransport', 'vehicleTransport'),
                    ('construction', 'construction'),
                    ('salesService', 'salesService'),
                    ('childRecreation', 'childRecreation'),
                    ('other', 'other'),
                    ('engineering', 'engineering'),
                    ('medicine', 'medicine'),
                    ('cs', 'cs'),
                    ('education', 'education'),
                    ('psychology', 'psychology'),
                    ('law', 'law'),
                    ('environment', 'environment'),
                    ('design', 'design'),
                    ('biology', 'biology'),
                    ('publicHealth', 'publicHealth'),
                    ('business', 'business'),
                    ('lifeScience', 'lifeScience'),
                    ('pharmacyTech', 'pharmacyTech'),
                    ('ambulance', 'ambulance'),
                    ('animalCare', 'animalCare'),
                    ('softwareDev', 'softwareDev'),
                    ('trainDriver', 'trainDriver'),
                    ('dentalNurse', 'dentalNurse'),
                    ('medicalAdmin', 'medicalAdmin'),
                    ('accounting', 'accounting'),
                    ('childcare', 'childcare'),
                    ('sport', 'sport'),
                ],
            ),
        ),
        migrations.AlterField(
            model_name='predefinedscholarship_sv',
            name='subject',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='predefinedscholarship_sv',
            name='study_level',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
