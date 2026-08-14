from django.urls import path

from waitlist.views import (
    AnalyticsAPIView,
    AnalyticsEventAPIView,
    EmailPipelineLogsAPIView,
    EmailPipelineSendAPIView,
    EmailTemplateAPIView,
    WaitlistCollectionAPIView,
    WaitlistDetailAPIView,
    WaitlistExportAPIView,
)

urlpatterns = [
    path("waitlist", WaitlistCollectionAPIView.as_view(), name="waitlist-collection"),
    path("waitlist/export", WaitlistExportAPIView.as_view(), name="waitlist-export"),
    path(
        "waitlist/<str:subscriber_id>",
        WaitlistDetailAPIView.as_view(),
        name="waitlist-detail",
    ),
    path(
        "email-pipeline/logs",
        EmailPipelineLogsAPIView.as_view(),
        name="email-pipeline-logs",
    ),
    path(
        "email-pipeline/send",
        EmailPipelineSendAPIView.as_view(),
        name="email-pipeline-send",
    ),
    path("email-template", EmailTemplateAPIView.as_view(), name="email-template"),
    path("analytics", AnalyticsAPIView.as_view(), name="analytics"),
    path("analytics/event", AnalyticsEventAPIView.as_view(), name="analytics-event"),
]
