from datetime import timedelta

from django.db import models
from django.utils import timezone

from helpers.models import UniqueUserId


def get_default_expiry():
    return timezone.now() + timedelta(days=1)


class Capsule(UniqueUserId):
    title = models.CharField(max_length=224)
    description = models.CharField(max_length=220, null=True, blank=True)
    creator = models.ForeignKey("capsulers.User", on_delete=models.CASCADE, related_name="created_capsules")
    log = models.TextField(blank=True)
    member = models.ManyToManyField("capsulers.User", related_name="capsules_joined", blank=True)
    contributor = models.ManyToManyField("capsulers.User", related_name="capsules_contributed_to", blank=True)
    private = models.BooleanField(default=True)
    maturity_date = models.DateTimeField(default=get_default_expiry, help_text="Time to open capsule")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_private(self):
        return self.private

    def is_open(self):
        if self.maturity_date <= timezone.now():
            return True
        return False

    def __repr__(self):
        return f"{self.title} is a private: {self.is_private}, capsule"


class Videos(UniqueUserId):
    capsule = models.ForeignKey("memories.Capsule", on_delete=models.CASCADE)
    video_title = models.CharField(max_length=100)
    video_file = models.URLField(max_length=512, blank=True)
    teaser = models.BooleanField(default=False)

    @property
    def use_for_teaser_generation(self):
        return bool(self.teaser)


class Images(UniqueUserId):
    capsule = models.ForeignKey("memories.Capsule", on_delete=models.CASCADE)
    image_title = models.CharField(max_length=100)
    image_file = models.URLField(max_length=512, blank=True)


class Teasers(UniqueUserId):
    video = models.ForeignKey("memories.Videos", on_delete=models.DO_NOTHING, related_name="preview")
    capsule = models.ForeignKey("memories.Capsule", on_delete=models.CASCADE, related_name="capsule_previews")
    teaser_url = models.URLField(max_length=512, blank=True)
