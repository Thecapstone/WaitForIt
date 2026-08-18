import logging

from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
import rest_framework.status as status
from rest_framework.throttling import UserRateThrottle
from rest_framework.viewsets import ModelViewSet

from memories.audit import record_capsule_event
from memories.models import Capsule, Capsule as capsule_db, CapsuleAuditLog
from memories.serializers import (
    CapsuleAuditLogSerializer,
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

    def create(self, request):
        serializer = CapsuleCreationSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            capsule: Capsule = serializer.save(creator=request.user)
            record_capsule_event(
                capsule,
                CapsuleAuditLog.Action.CREATED,
                entity_type=CapsuleAuditLog.EntityType.CAPSULE,
                entity_id=capsule.id,
                actor=request.user,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk):
        """
        View all capsule content, by members, once the open date reaches.
        """
        try:
            capsule = capsule_db.objects.get(id=pk)
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
        record_capsule_event(
            capsule,
            CapsuleAuditLog.Action.VIEWED,
            entity_type=CapsuleAuditLog.EntityType.CAPSULE,
            entity_id=capsule.id,
            actor=request.user,
        )
        return Response(
            {
                "data": serializer.data,
                "message": "Here's a glimpse of your stored memories.",
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request, pk, *args, **kwargs):
        """
        Update capsule data by contributors or creator not members.
        """
        try:
            capsule = capsule_db.objects.get(id=pk)
        except capsule_db.DoesNotExist:
            return Response(
                {"Capsule": "Capsule does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        # NOTE: This update() previously built the serializer from the instance
        # only (CapsuleUpdateSerializer(capsule)), so is_valid()/save() were
        # never called and the capsule was never persisted. FIXED: it now passes
        # request.data through validation and actually saves the changes.
        if request.user == capsule.creator or request.user in capsule.contributor.all():
            serializer = CapsuleUpdateSerializer(
                capsule,
                data=request.data,
                partial=kwargs.get("partial", False),
            )
            if serializer.is_valid():
                serializer.save()
                record_capsule_event(
                    capsule,
                    CapsuleAuditLog.Action.UPDATED,
                    entity_type=CapsuleAuditLog.EntityType.CAPSULE,
                    entity_id=capsule.id,
                    actor=request.user,
                )
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"message": "Cannot access this capsule"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="create-log",
        permission_classes=[permissions.IsAuthenticated],
    )
    def create_log(self, request, pk):
        try:
            capsule = capsule_db.objects.get(id=pk)
        except capsule_db.DoesNotExist:
            return Response(
                {"Capsule": "Capsule does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = LogCreationSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            log = serializer.save(creator=request.user, capsule=capsule)
            record_capsule_event(
                capsule,
                CapsuleAuditLog.Action.LOG_ADDED,
                entity_type=CapsuleAuditLog.EntityType.LOG,
                entity_id=log.id,
                actor=request.user,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(responses=CapsuleAuditLogSerializer(many=True))
    @action(
        detail=True,
        methods=["get"],
        url_path="audit-logs",
        permission_classes=[permissions.IsAuthenticated],
    )
    def audit_logs(self, request, pk):
        """
        Read a capsule's audit trail. Only the creator or contributors may view it.
        """
        try:
            capsule = capsule_db.objects.get(id=pk)
        except capsule_db.DoesNotExist:
            return Response(
                {"Capsule": "Capsule does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if (
            request.user != capsule.creator
            and request.user not in capsule.contributor.all()
        ):
            return Response(
                {"message": "Cannot access this capsule"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        entries = CapsuleAuditLog.objects.filter(capsule=capsule)
        serializer = CapsuleAuditLogSerializer(entries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["get"],
        url_path="log",
        permission_classes=[permissions.IsAuthenticated],
    )
    def retrieve_log(self, request):
        serializer = LogViewSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
