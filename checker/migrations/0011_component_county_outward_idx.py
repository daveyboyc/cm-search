# Generated by Django 5.1.6 on 2025-05-11 19:29

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("checker", "0010_component_year_loc_idx"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="component",
            index=models.Index(
                fields=["county", "outward_code"], name="county_outward_idx"
            ),
        ),
    ]
