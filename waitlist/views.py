# views.py

from datetime import date

from django.db.models import Count
from django.db.models.functions import TruncDate
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from helpers.enums import WaitListFilterKey
from waitlist.models import WaitList
from waitlist.serializers import WaitListSerializer


class WaitListViewSet(viewsets.GenericViewSet):
    queryset = WaitList.objects.all()
    serializer_class = WaitListSerializer

    def get_permissions(self):
        """
        Waitlist signup is public.
        Metrics/administrative endpoints require admin access.
        """

        if self.action == "create":
            return [AllowAny()]

        return [IsAdminUser()]

    def create(self, request):
        """
        POST /waitlist/

        Public endpoint for joining the WaitForIt waitlist.
        """

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
        """
        GET /waitlist/activity/

        Aggregate waitlist signups by calendar date.
        """

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

        return Response(
            {
                "data": data,
            }
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="overview",
    )
    def overview(self, request):
        """
        GET /waitlist/overview/

        Return summary metrics and role breakdown.
        """

        total_signups = WaitList.objects.count()

        developers = WaitList.objects.filter(
            is_develoeper=True
        ).count()

        non_developers = WaitList.objects.filter(
            is_develoeper=False
        ).count()

        role_breakdown = (
            WaitList.objects
            .values("role")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        return Response(
            {
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
            }
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="filter",
    )
    def filter_signups(self, request):
        """
        GET /waitlist/filter/?key=role&value=Backend%20Engineer
        GET /waitlist/filter/?key=date&value=2026-08-10
        """

        key = request.query_params.get("key")
        value = request.query_params.get("value")

        if not key or not value:
            return Response(
                {
                    "detail": "Both 'key' and 'value' are required."
                },
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
                        f"{', '.join(
                            item.value
                            for item in WaitListFilterKey
                        )}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = WaitList.objects.all()

        if filter_key == WaitListFilterKey.ROLE:
            queryset = queryset.filter(
                role__iexact=value
            )

        elif filter_key == WaitListFilterKey.DATE:
            try:
                filter_date = date.fromisoformat(value)
            except ValueError:
                return Response(
                    {
                        "detail": (
                            "Invalid date format. "
                            "Expected YYYY-MM-DD."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            queryset = queryset.filter(
                created_at__date=filter_date
            )

        queryset = queryset.order_by("-created_at")

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(
            {
                "filter": {
                    "key": filter_key.value,
                    "value": value,
                },
                "count": queryset.count(),
                "data": serializer.data,
            }
        )
