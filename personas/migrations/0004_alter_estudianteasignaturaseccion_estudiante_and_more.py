# Generated by Django 5.2.2 on 2025-06-13 20:39

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0003_remove_estudiante_seccion_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='estudianteasignaturaseccion',
            name='estudiante',
            field=models.ForeignKey(limit_choices_to={'user_type': 'estudiante'}, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.DeleteModel(
            name='Estudiante',
        ),
    ]
