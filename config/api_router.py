from rest_framework import routers

from authentication.views import AuthViewSet
from memories.views import CapsuleViewSet

app_name = "api"

router = routers.SimpleRouter()
router.register(r"memories", CapsuleViewSet, basename="memories")
router.register(r"auth", AuthViewSet, basename="auth")

urlpatterns = router.urls
