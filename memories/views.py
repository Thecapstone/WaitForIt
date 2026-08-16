import logging

from django.db import IntegrityError
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
import rest_framework.status as status
from rest_framework.throttling import UserRateThrottle
from rest_framework.viewsets import ModelViewSet

from helpers.idempotency import cached_response, remember_response, request_fingerprint
from memories.models import Capsule as capsule_db, Logs as logs_db
from memories.serializers import (
    CapsuleCreationSerializer,
    # CapsuleJoinSerializer,
    # CapsulePreviewSerializer,
    CapsuleUpdateSerializer,
    CapsuleViewSerializer,
    LogCreationSerializer,
    LogViewSerializer,
)

logger = logging.getLogger("waitforit")


class TwicePerDayUserThrottle(UserRateThrottle):
    rate = "2/day"


class CapsuleViewSet(ModelViewSet):
    queryset = capsule_db.objects.all()
    serializer_class = CapsuleCreationSerializer
    permission_classes = [permissions.AllowAny]

    @action(
        detail=False,
        methods=["POST"],
        url_path=r"create",
        permission_classes=[permissions.AllowAny],
    )
    def create_capsules(self, request):
        idempotency_key = request_fingerprint(request, "capsule-create")
        cached = cached_response(idempotency_key)
        if cached:
            return cached

        serializer = CapsuleCreationSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            try:
                serializer.save(creator=request.user)
            except IntegrityError:
                return Response(
                    {"title": ["Capsule with this name already exists."]},
                    status=status.HTTP_409_CONFLICT,
                )
            return remember_response(
                idempotency_key,
                Response(serializer.data, status=status.HTTP_201_CREATED),
            )
        response_status = (
            status.HTTP_409_CONFLICT
            if "title" in serializer.errors
            and "already exists" in str(serializer.errors["title"])
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(serializer.errors, status=response_status)

    @action(
        detail=True,
        methods=["GET"],
        url_path=r"view",
        permission_classes=[permissions.AllowAny],
    )
    def retrieve_capsule(self, request, pk):
        """
        View all capsule content, by members, once the open date reaches.
        """
        idempotency_key = request_fingerprint(request, "capsule-view", pk)
        cached = cached_response(idempotency_key)
        if cached:
            return cached

        try:
            capsule = capsule_db.objects.prefetch_related("member", "logs").get(id=pk)
        except capsule_db.DoesNotExist:
            return Response(
                {"Capsule": "Capsule does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = CapsuleViewSerializer(capsule)

        if (
            request.user != capsule.creator
            and request.user not in capsule.member.all()
            and not capsule.is_open()
        ):
            return Response(
                {"message": "Cannot access this capsule"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return remember_response(
            idempotency_key,
            Response(
                {
                    "data": serializer.data,
                    "message": "Here's a glimpse of your stored memories.",
                },
                status=status.HTTP_200_OK,
            ),
        )

    @action(
        detail=True,
        methods=["PATCH"],
        url_path=r"update",
        permission_classes=[permissions.AllowAny],
    )
    def update_capsule(self, request, pk):
        """
        Update capsule data by contributors or creator not members.
        """
        try:
            capsule = capsule_db.objects.get(id=pk)
        except capsule_db.DoesNotExist:
            return Response(
                {"Capsule": "Capsule does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = CapsuleUpdateSerializer(capsule)

        if request.user == capsule.creator or request.user in capsule.contributor.all():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"message": "Cannot access this capsule"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    @action(
        detail=True,
        methods=["POST"],
        url_path="create-log",
        permission_classes=[permissions.AllowAny],
    )
    def create_log(self, request, pk):
        idempotency_key = request_fingerprint(request, "log-create", pk)
        cached = cached_response(idempotency_key)
        if cached:
            return cached

        capsule = capsule_db.objects.get(id=pk)
        serializer = LogCreationSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            serializer.save(creator=request.user, capsule=capsule)
            return remember_response(
                idempotency_key,
                Response(serializer.data, status=status.HTTP_201_CREATED),
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=["get"],
        url_path="log",
        permission_classes=[permissions.AllowAny],
    )
    def retrieve_log(self, request, pk=None):
        idempotency_key = request_fingerprint(request, "log-view", pk)
        cached = cached_response(idempotency_key)
        if cached:
            return cached

        logs = logs_db.objects.filter(capsule_id=pk).prefetch_related(
            "images",
            "videos",
        )
        serializer = LogViewSerializer(logs, many=True)
        return remember_response(
            idempotency_key,
            Response({"data": serializer.data}, status=status.HTTP_200_OK),
        )

    # @action(
    #     detail=False,
    #     methods=["get"],
    #     url_path="capsule-preview",
    #     permission_classes=[permissions.IsAuthenticated],
    # )
    # def preview(self, request, pk):
    #     """
    #     View limited capsule content, before maturity
    #     """
    #     try:
    #         capsule = capsule_db.objects.get(id=pk)
    #     except capsule_db.DoesNotExist:
    #         return Response(
    #             {"Capsule": "Capsule does not exist"}, status=status.HTTP_404_NOT_FOUND
    #         )
    #     serializer = CapsulePreviewSerializer(capsule)

    #     if request.user == capsule.creator or request.user == capsule.members:
    #         return Response(serializer.data, status=status.HTTP_200_OK)
    #     return Response(
    #         {"message": "Cannot access this capsule"},
    #         status=status.HTTP_401_UNAUTHORIZED,
    #     )

    # def join_capsule(self, request, pk):
    #     """
    #     returns the id of the user and the id of the capsule they want to join.
    #     """
    #     try:
    #         capsule = capsule_db.objects.get(id=pk)
    #     except capsule_db.DoesNotExist:
    #         return Response(
    #             {"Capsule": "Capsule does not exist"}, status=status.HTTP_404_NOT_FOUND
    #         )

    #     data = {"user_id": request.user, "capsule_id": capsule}
    #     serializer = CapsuleJoinSerializer(data=data)

    #     if serializer.is_valid:
    #         serializer.save()
    #         capsule.members.add(request.user)
    #         user_db.objects.get(id=request.user.id).capsules_joined.add(capsule)
    #         return Response(serializer.data, status=status.HTTP_200_OK)
    #     return Response(
    #         {"message": "Capsule or user not found"}, status=status.HTTP_400_BAD_REQUEST
    #     )

    # likely need to seperate the adding of new members and the adding of new contributors.
    # def add_new_member_to_capsule(self, request, capsule_id, user_id):
    #     """
    #     #retrieves capsule with a given id and the id of the user to be made a contributor,
    #     #adds the capsule id to the 'capsules_contributed_to reverse many-to-many user field,
    #     #finally add the user id to the contributors list which grants them specific permissions.
    #     """
    #     try:
    #         capsule = capsule_db.objects.get(id=capsule_id)
    #     except capsule_db.DoesNotExist:
    #         return Response(
    #             {"Capsule": "Capsule does not exist"}, status=status.HTTP_404_NOT_FOUND
    #         )
    #     try:
    #         user = user_db.objects.get(id=user_id)
    #     except user_db.DoesNotExist:
    #         return Response(
    #             {"message": "User not found"}, status=status.HTTP_400_BAD_REQUEST
    #         )

    #     if request.user == capsule.creator and request.user not in capsule.contributors:
    #         capsule.contributors.add(user)
    #         user.capsules_contributed_to.add(capsule)
    #         return capsule
    #     return Response(
    #         {"message": "Unauthorized to share this capsule"},
    #         status=status.HTTP_401_UNAUTHORIZED,
    #     )
