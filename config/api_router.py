from rest_framework import routers

from authentication.views import AuthViewSet
from memories.views import CapsuleViewSet
from waitlist.views import WaitListViewSet

app_name = "api"

router = routers.SimpleRouter()
router.register(r"memories", CapsuleViewSet, basename="memories")
router.register(r"auth", AuthViewSet, basename="auth")
router.register(r"waitlist", WaitListViewSet, basename="waitlist")

urlpatterns = router.urls
