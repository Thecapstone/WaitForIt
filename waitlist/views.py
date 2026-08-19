import csv
from datetime import date

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from helpers.enums import WaitListFilterKey
from waitlist.models import AnalyticsEvent, EmailDeliveryLog, EmailTemplate, WaitList
from waitlist.serializers import (
    AnalyticsEventSerializer,
    EmailDeliveryLogSerializer,
    EmailTemplateSerializer,
    WaitListSerializer,
)


class WaitListViewSet(viewsets.GenericViewSet):
    queryset = WaitList.objects.all()
    serializer_class = WaitListSerializer

    def get_permissions(self):
        """
        Legacy waitlist signup is public.
        Metrics/administrative endpoints require admin access.
        """

        if self.action == "create":
            return [AllowAny()]

        return [IsAdminUser()]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        waitlist_user = serializer.save()

        return Response(
            {
                "message": "Successfully joined the WaitForIt waitlist.",
                "data": self.get_serializer(waitlist_user).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="activity",
    )
    def activity(self, request):
        activity = (
            WaitList.objects
            .annotate(signup_date=TruncDate("created_at"))
            .values("signup_date")
            .annotate(signups=Count("id"))
            .order_by("signup_date")
        )

        data = [
            {
                "date": item["signup_date"].isoformat(),
                "signups": item["signups"],
            }
            for item in activity
        ]

        return Response({
            "data": data,
        })

    @action(
        detail=False,
        methods=["get"],
        url_path="overview",
    )
    def overview(self, request):
        total_signups = WaitList.objects.count()
        developers = WaitList.objects.filter(is_developer=True).count()
        non_developers = WaitList.objects.filter(is_developer=False).count()

        role_breakdown = (
            WaitList.objects
            .values("role")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        return Response({
            "total_signups": total_signups,
            "developers": developers,
            "non_developers": non_developers,
            "role_breakdown": [
                {
                    "role": item["role"],
                    "count": item["count"],
                }
                for item in role_breakdown
            ],
        })

    @action(
        detail=False,
        methods=["get"],
        url_path="filter",
    )
    def filter_signups(self, request):
        key = request.query_params.get("key")
        value = request.query_params.get("value")

        if not key or not value:
            return Response(
                {"detail": "Both 'key' and 'value' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            filter_key = WaitListFilterKey(key)
        except ValueError:
            return Response(
                {
                    "detail": (
                        f"Invalid filter key '{key}'. "
                        f"Allowed keys are: "
                        f"{', '.join(item.value for item in WaitListFilterKey)}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = WaitList.objects.all()

        if filter_key == WaitListFilterKey.ROLE:
            queryset = queryset.filter(role__iexact=value)

        elif filter_key == WaitListFilterKey.DATE:
            try:
                filter_date = date.fromisoformat(value)
            except ValueError:
                return Response(
                    {"detail": ("Invalid date format. Expected YYYY-MM-DD.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            queryset = queryset.filter(created_at__date=filter_date)

        queryset = queryset.order_by("-created_at")
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            "filter": {
                "key": filter_key.value,
                "value": value,
            },
            "count": queryset.count(),
            "data": serializer.data,
        })


class WaitlistCollectionAPIView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get_queryset(self, request):
        queryset = WaitList.objects.all().order_by("-created_at")
        search = request.query_params.get("search")
        role = request.query_params.get("role")
        subscriber_status = request.query_params.get("status")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(email__icontains=search)
                | Q(role__icontains=search)
                | Q(source__icontains=search)
            )
        if role:
            queryset = queryset.filter(role__iexact=role)
        if subscriber_status:
            queryset = queryset.filter(status=subscriber_status)

        return queryset

    def get(self, request):
        queryset = self.get_queryset(request)
        serializer = WaitListSerializer(queryset, many=True)
        return Response({
            "count": queryset.count(),
            "data": serializer.data,
        })

    def post(self, request):
        serializer = WaitListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscriber = serializer.save()

        return Response(
            {
                "message": "Successfully joined the WaitForIt waitlist.",
                "data": WaitListSerializer(subscriber).data,
            },
            status=status.HTTP_201_CREATED,
        )


class WaitlistDetailAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get_object(self, subscriber_id):
        return get_object_or_404(WaitList, id=subscriber_id)

    def put(self, request, subscriber_id):
        subscriber = self.get_object(subscriber_id)
        serializer = WaitListSerializer(subscriber, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "message": "Subscriber updated successfully.",
            "data": serializer.data,
        })

    def delete(self, request, subscriber_id):
        subscriber = self.get_object(subscriber_id)
        subscriber.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WaitlistExportAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        queryset = WaitlistCollectionAPIView().get_queryset(request)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="waitlist-subscribers.csv"'
        )

        writer = csv.writer(response)
        writer.writerow([
            "id",
            "name",
            "email",
            "is_developer",
            "role",
            "source",
            "status",
            "created_at",
        ])

        for subscriber in queryset:
            writer.writerow([
                subscriber.id,
                subscriber.name,
                subscriber.email,
                subscriber.is_developer,
                subscriber.role,
                subscriber.source,
                subscriber.status,
                subscriber.created_at.isoformat(),
            ])

        return response


class EmailPipelineLogsAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        logs = EmailDeliveryLog.objects.select_related("subscriber").order_by(
            "-created_at"
        )
        serializer = EmailDeliveryLogSerializer(logs, many=True)
        return Response({
            "count": logs.count(),
            "data": serializer.data,
        })


class EmailPipelineSendAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = EmailDeliveryLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        log = serializer.save()

        return Response(
            {
                "message": "Welcome email log created.",
                "data": EmailDeliveryLogSerializer(log).data,
            },
            status=status.HTTP_201_CREATED,
        )


class EmailTemplateAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get_template(self):
        template = (
            EmailTemplate.objects.filter(is_active=True).order_by("-created_at").first()
        )
        if template:
            return template

        return EmailTemplate.objects.create(
            subject="Welcome to WaitForIt",
            body="Thanks for joining the WaitForIt waitlist.",
            is_active=True,
        )

    def get(self, request):
        template = self.get_template()
        return Response({
            "data": EmailTemplateSerializer(template).data,
        })

    def put(self, request):
        template = self.get_template()
        serializer = EmailTemplateSerializer(template, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(is_active=True)

        return Response({
            "message": "Welcome email template updated.",
            "data": serializer.data,
        })


class AnalyticsAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        total_subscribers = WaitList.objects.count()
        developers = WaitList.objects.filter(is_developer=True).count()
        non_developers = WaitList.objects.filter(is_developer=False).count()

        by_status = (
            WaitList.objects
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        by_role = (
            WaitList.objects
            .values("role")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        email_statuses = (
            EmailDeliveryLog.objects
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        recent_events = AnalyticsEvent.objects.select_related("subscriber").order_by(
            "-created_at"
        )[:20]

        return Response({
            "summary": {
                "total_subscribers": total_subscribers,
                "developers": developers,
                "non_developers": non_developers,
                "email_logs": EmailDeliveryLog.objects.count(),
                "analytics_events": AnalyticsEvent.objects.count(),
            },
            "subscribers_by_status": list(by_status),
            "subscribers_by_role": list(by_role),
            "email_delivery_by_status": list(email_statuses),
            "recent_events": AnalyticsEventSerializer(recent_events, many=True).data,
        })


class AnalyticsEventAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = AnalyticsEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save()

        return Response(
            {
                "message": "Analytics event recorded.",
                "data": AnalyticsEventSerializer(event).data,
            },
            status=status.HTTP_201_CREATED,
        )
