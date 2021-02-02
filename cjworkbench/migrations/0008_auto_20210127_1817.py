# Generated by Django 3.1.5 on 2021-01-27 18:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cjworkbench", "0007_auto_20210126_2001"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="max_fetches_per_day",
            field=models.IntegerField(
                default=50,
                help_text="Applies to the sum of all this user's Workflows. One fetch every 5min = 288 fetches per day.",
            ),
        ),
    ]