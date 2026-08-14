from django.db import models

from helpers.models import UniqueUserId


class WaitList(UniqueUserId):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        CONVERTED = "converted", "Converted"
        UNSUBSCRIBED = "unsubscribed", "Unsubscribed"

    name = models.CharField(max_length=90, blank=False)
    email = models.EmailField(unique=True, blank=False)
    is_developer = models.BooleanField(default=True)
    role = models.CharField(max_length=90)
    source = models.CharField(max_length=90, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    created_at = models.DateTimeField(auto_now_add=True)


class EmailTemplate(UniqueUserId):
    subject = models.CharField(max_length=160)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class EmailDeliveryLog(UniqueUserId):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    subscriber = models.ForeignKey(
        WaitList,
        related_name="email_logs",
        on_delete=models.CASCADE,
    )
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=160)
    body = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)


class AnalyticsEvent(UniqueUserId):
    event = models.CharField(max_length=100)
    subscriber = models.ForeignKey(
        WaitList,
        related_name="analytics_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    visitor_id = models.CharField(max_length=120, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
