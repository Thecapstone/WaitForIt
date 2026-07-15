from django.urls import path
from rest_framework import routers

from authentication.views import AuthViewSet
from health.views import HealthCheckView
from memories.views import CapsuleViewSet

app_name = "api"

router = routers.SimpleRouter()
router.register(r"memories", CapsuleViewSet, basename="memories")
router.register(r"auth", AuthViewSet, basename="auth")

urlpatterns = [
    path("health", HealthCheckView.as_view(), name="health-check"),
]

urlpatterns += router.urls
