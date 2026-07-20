from uuid import uuid4

import auto_prefetch
from django.db import models


def generate_unique_id() -> str:
    """
    Number of Possibilities = 16^8

    Here, 16 represents the number of possible hexadecimal characters
    (0-9 and a-f), and 8 is the length of the substring.

    Calculating it:

    16^10 = 1,099,511,627,776
    """

    return uuid4().hex[:10]


class TimeBasedModel(auto_prefetch.Model):
    id = models.UUIDField(
        default=generate_unique_id,
        editable=False,
        primary_key=True,
        serialize=False,
        unique=True,
    )
    visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(auto_prefetch.Model.Meta):
        abstract = True

    objects = auto_prefetch.Manager()


class UniqueUserId(TimeBasedModel):
    id = models.CharField(
        primary_key=True,
        default=generate_unique_id,
        help_text="unique id generator for anonymous usernames",
        editable=False,
        serialize=False,
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    visible = models.BooleanField(default=True)

    class Meta(auto_prefetch.Model.Meta):
        abstract = True

    def __str__(self):
        return self.id
