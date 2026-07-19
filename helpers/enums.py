from django.db.models import TextChoices
from payment.views import payment_callback


class UserPlan(TextChoices):
    Basic = {"basic": "basic"}
    Premium = {"premium": "premium"}
