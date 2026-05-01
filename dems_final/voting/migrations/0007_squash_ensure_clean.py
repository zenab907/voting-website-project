"""
Migration 0007: Ensure face_descriptor field is correctly typed.
This is a documentation migration — safe no-op if field already exists.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('voting', '0006_voter_face_descriptor_upgrade'),
    ]

    operations = [
        migrations.AlterField(
            model_name='voter',
            name='face_descriptor',
            field=models.TextField(
                blank=True,
                null=True,
                help_text=(
                    "128-float face-api.js descriptor stored as JSON array. "
                    "No raw images are ever stored. Works cross-device via central DB."
                ),
            ),
        ),
    ]
