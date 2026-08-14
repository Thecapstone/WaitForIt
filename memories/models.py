from datetime import timedelta

import auto_prefetch
from django.db import models
from django.utils import timezone

from helpers.models import UniqueUserId


def get_default_expiry():
    return timezone.now() + timedelta(days=1)


class Capsule(UniqueUserId):
    title = models.CharField(max_length=224)
    description = models.CharField(max_length=220, null=True, blank=True)
    image = models.URLField(max_length=512, blank=True)
    creator = models.ForeignKey(
        "authentication.User", on_delete=models.CASCADE, related_name="capsule"
    )
    member = models.ManyToManyField(
        "authentication.User", related_name="capsules_joined", blank=True
    )
    contributor = models.ManyToManyField(
        "authentication.User", related_name="capsules_contributed_to", blank=True
    )
    private = models.BooleanField(default=True)
    maturity_date = models.DateTimeField(
        default=get_default_expiry, help_text="Time to open capsule"
    )
    previous_article = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_private(self):
        return self.private

    def is_open(self):
        if self.maturity_date <= timezone.now():
            return True
        return False

    def __repr__(self):
        return f"{self.title} is a private: {self.is_private}, capsule"

    def __str__(self):
        return self.title


class Logs(UniqueUserId):
    capsule = models.ForeignKey(Capsule, on_delete=models.CASCADE, related_name="logs")
    creator = models.ForeignKey(
        "authentication.User", on_delete=models.CASCADE, related_name="logs"
    )
    stamp = models.CharField(max_length=120)
    title = models.CharField(max_length=100)
    description = models.TextField()
    code_language = models.CharField(max_length=80, blank=True)
    code_framework = models.CharField(max_length=80, blank=True)
    is_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)


class CapsuleAuditLog(UniqueUserId):
    class Event(models.TextChoices):
        CREATED = "CREATED", "Capsule created"
        VIEWED = "VIEWED", "Capsule viewed"
        UPDATED = "UPDATED", "Capsule updated"
        LOG_ADDED = "LOG_ADDED", "Log added to capsule"
        ARTICLE_GENERATED = "ARTICLE_GENERATED", "Article generated for capsule"
        MEMBER_ADDED = "MEMBER_ADDED", "Member added to capsule"
        MEMBER_REMOVED = "MEMBER_REMOVED", "Member removed from capsule"
        CONTRIBUTOR_ADDED = "CONTRIBUTOR_ADDED", "Contributor added to capsule"
        CONTRIBUTOR_REMOVED = "CONTRIBUTOR_REMOVED", "Contributor removed from capsule"

    capsule = models.ForeignKey(
        Capsule, on_delete=models.CASCADE, related_name="audit_logs"
    )
    actor = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="capsule_audit_logs",
    )
    event = models.CharField(max_length=32, choices=Event.choices)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(auto_prefetch.Model.Meta):  # type: ignore[reportIncompatibleVariableOverride]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["capsule", "created_at"]),
        ]


class Videos(UniqueUserId):
    capsule = models.ForeignKey(
        Capsule, on_delete=models.CASCADE, related_name="videos"
    )
    log = models.ForeignKey(Logs, on_delete=models.CASCADE, related_name="videos")
    video_title = models.CharField(max_length=100)
    video_file = models.URLField(max_length=512, blank=True)
    teaser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    @property
    def use_for_teaser_generation(self):
        return bool(self.teaser)


class Images(UniqueUserId):
    capsule = models.ForeignKey(
        Capsule, on_delete=models.CASCADE, related_name="images"
    )
    log = models.ForeignKey(Logs, on_delete=models.CASCADE, related_name="images")
    image_title = models.CharField(max_length=100)
    image_file = models.URLField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)


class Teasers(UniqueUserId):
    video = models.ForeignKey(
        "memories.Videos", on_delete=models.DO_NOTHING, related_name="preview"
    )
    capsule = models.ForeignKey(
        "memories.Capsule", on_delete=models.CASCADE, related_name="video_previews"
    )
    teaser_url = models.URLField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)


class Tag(models.Model):
    # Unique ensures no duplicate tags are created
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Articles(UniqueUserId):
    title = models.CharField(max_length=120)
    capsule_id = models.ForeignKey(
        "memories.Capsule", on_delete=models.CASCADE, related_name="articles"
    )
    log = models.ForeignKey(Logs, on_delete=models.CASCADE, related_name="articles")
    logs = models.ManyToManyField(
        Logs,
        related_name="aggregated_articles",
        blank=True,
    )
    tags = models.ForeignKey(
        "memories.Tag", on_delete=models.DO_NOTHING, related_name="article"
    )
    body = models.TextField()
    image = models.URLField(max_length=512, blank=True)

    def __str__(self):
        return self.title
