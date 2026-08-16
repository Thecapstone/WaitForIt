from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0006_remove_sessions_payload_data_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sessions",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
    ]
