from django.urls import path

# from memories.views import UploadImageForm
from memories import views

urlpatterns = [
    path("", views.CreateCapsule, name="images"),
    path("capsules/", views.CapsuleViewSet.as_view({"get": "list"}), name="capsules"),
]

# app_name='memories'
