

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0002_patient_unique_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patient',
            name='national_code',
            field=models.CharField(max_length=10, unique=True),
        ),
    ]
