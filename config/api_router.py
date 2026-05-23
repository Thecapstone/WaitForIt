from rest_framework import routers
from memories.views import CapsuleViewSet
from capsulers.views import UserViewSet, AuthViewSet
from health.views import HealthCheckView
from django.urls import path

app_name = "api"

router = routers.SimpleRouter()
router.register(r'memories', CapsuleViewSet, basename='memories')
router.register(r'users', UserViewSet, basename='users')
router.register(r'auth', AuthViewSet, basename='auth')

urlpatterns = [
    path('health', HealthCheckView.as_view(), name='health-check'),
]

urlpatterns += router.urls