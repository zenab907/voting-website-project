from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('voting', '0004_remove_voter_last_auth_timestamp_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='voter',
            name='face_descriptor',
            field=models.TextField(
                blank=True,
                null=True,
                help_text='Face-API.js 128-D descriptor stored as JSON array'
            ),
        ),
    ]
