# Generated for waitlist v1 API.

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager

import helpers.models


class Migration(migrations.Migration):
    dependencies = [
        ("waitlist", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="waitlist",
            old_name="fullname",
            new_name="name",
        ),
        migrations.AddField(
            model_name="waitlist",
            name="source",
            field=models.CharField(blank=True, default="", max_length=90),
        ),
        migrations.AddField(
            model_name="waitlist",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "New"),
                    ("contacted", "Contacted"),
                    ("converted", "Converted"),
                    ("unsubscribed", "Unsubscribed"),
                ],
                default="new",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="EmailTemplate",
            fields=[
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.CharField(
                        default=helpers.models.generate_unique_id,
                        editable=False,
                        help_text="unique id generator for anonymous usernames",
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("visible", models.BooleanField(default=True)),
                ("subject", models.CharField(max_length=160)),
                ("body", models.TextField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "abstract": False,
                "base_manager_name": "prefetch_manager",
            },
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name="AnalyticsEvent",
            fields=[
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.CharField(
                        default=helpers.models.generate_unique_id,
                        editable=False,
                        help_text="unique id generator for anonymous usernames",
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("visible", models.BooleanField(default=True)),
                ("event", models.CharField(max_length=100)),
                (
                    "visitor_id",
                    models.CharField(blank=True, default="", max_length=120),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "subscriber",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="analytics_events",
                        to="waitlist.waitlist",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "prefetch_manager",
            },
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name="EmailDeliveryLog",
            fields=[
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.CharField(
                        default=helpers.models.generate_unique_id,
                        editable=False,
                        help_text="unique id generator for anonymous usernames",
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("visible", models.BooleanField(default=True)),
                ("recipient_email", models.EmailField(max_length=254)),
                ("subject", models.CharField(max_length=160)),
                ("body", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                        ],
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "subscriber",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_logs",
                        to="waitlist.waitlist",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "prefetch_manager",
            },
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
    ]
