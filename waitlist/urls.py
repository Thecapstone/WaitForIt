from django.urls import path

from waitlist.views import (
    WaitListActivityView,
    WaitListFilterView,
    WaitListSignupView,
)

urlpatterns = [
    path(
        "waitlist/",
        WaitListSignupView.as_view(),
        name="waitlist-signup",
    ),
    path(
        "waitlist/activity/",
        WaitListActivityView.as_view(),
        name="waitlist-activity",
    ),
    path(
        "waitlist/filter/",
        WaitListFilterView.as_view(),
        name="waitlist-filter",
    ),
]
