from django.db import models

from helpers.models import UniqueUserId


class WaitList(UniqueUserId):
    fullname = models.CharField(max_length=90, blank=False)
    email = models.EmailField(unique=True, blank=False)
    is_developer = models.BooleanField(default=True)
    role = models.CharField(max_length=90)
    created_at = models.DateTimeField(auto_now_add=True)
