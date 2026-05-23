from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser
from capsulers.managers import UserManager
from django.utils.translation import gettext_lazy as _
import auto_prefetch

# Create your models here.


class User(AbstractUser):
    username = None
    first_name = None
    last_name = None

    email = models.EmailField(_("email address"), unique=True)
    
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(_("last login"), blank=True, null=True)
    is_premium = models.BooleanField(default=False)
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})
    
   
    objects = UserManager()
