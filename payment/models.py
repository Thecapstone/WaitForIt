from django.db import models

from authentication.models import User


class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    txn_ref = models.CharField(max_length=200)
    amount = models.IntegerField()
    status = models.CharField(max_length=20)
