"""
Migration: ensure face_descriptor field exists and is properly typed.
Safe to run on existing DB — uses get_or_create pattern.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('voting', '0005_voter_face_descriptor'),
    ]

    operations = [
        # face_descriptor already exists from migration 0005
        # This migration is a no-op but documents the upgrade
        migrations.AlterField(
            model_name='voter',
            name='face_descriptor',
            field=models.TextField(
                blank=True,
                help_text='128-float face-api.js descriptor as JSON array — no raw images stored',
                null=True,
            ),
        ),
    ]
