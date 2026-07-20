from django.urls import path

from payment.views import initiate_payment, payment_callback

urlpatterns = [
    path("", initiate_payment, name="pay"),
    path("success/", payment_callback, name="pay-redirect"),
]
