# Generated by Django 4.0.4 on 2022-08-04 18:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0003_alter_olympiadparticipation_is_team_member_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='gender',
            field=models.CharField(choices=[('m', 'Мужской'), ('f', 'Женский')], max_length=2, null=True, verbose_name='Пол'),
        ),
    ]
