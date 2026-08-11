from django.db.models import TextChoices


class UserPlan(TextChoices):
    Basic = "basic", "basic"
    Premium = "premium", "premium"


class WaitListFilterKey(TextChoices):
    ROLE = "role"
    DATE = "date"
