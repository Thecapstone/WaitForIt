"""Authentication views handling user registration, login, and logout."""

import hashlib
import os
from tokenize import TokenError
from typing import Any
from uuid import uuid4

import jwt
from django.contrib.auth import get_user_model
from django.db.models import F
from django.utils import timezone
from ipware import get_client_ip
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from user_agents.parsers import parse

from authentication.models import Sessions as session_db
from authentication.models import User as user_db
from authentication.serializers import (
    CreateAdminSerializer,
    ForgotPasswordSerializer,
    UserCreateSerializer,
    UserLoginSerializer,
)

User = get_user_model()
SESSION_SECRET = os.getenv("SESSION_SECRET")
ALGORITHM = "HS256"


def create_user_agent(u_agent: str, ip: str) -> str:
    """Generate a stable, hashed device fingerprint from IP and User Agent."""
    ip_addr = ".".join(ip.split(".")[:2])
    user_agent = parse(u_agent)
    stable_string = f"{user_agent.os.family}--{user_agent.browser.family}--{user_agent.is_mobile}--{ip_addr}"

    return hashlib.sha256(stable_string.encode("utf-8")).hexdigest()


def session_token(user_id: int, role: str, session_version: int, request) -> str:
    """Build and hash a tracking payload tracking user session versions."""
    active_devices = create_user_agent(user_agent, ip_address)
    ip_address, _ = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    fingerprint = hashlib.sha256(uuid4().bytes).hexdigest()
    payload = {
        "user_id": user_id,
        "role": role,
        "session_version": session_version + 1,
        "active_devices": active_devices,
    }
    # return hashlib.sha256(str(payload).encode("utf-8")).hexdigest()
    return jwt.encode({"payload": payload}, SESSION_SECRET, algorithm=ALGORITHM)


class HasBootstrapToken(permissions.BasePermission):
    """Allows access only if the client provides the correct secret master key."""

    def is_allowed(self, request, view):
        # Fetch the secret token from the server environment
        secret_key = os.environ.get("ADMIN_BOOTSTRAP_TOKEN")
        admin_token = jwt.encode({"key": secret_key}, "admin_key", algorithm="HS256")
        if not secret_key:
            return False  # Secure by default if env variable is missing

        # Check for matching HTTP Header (e.g., 'X-Bootstrap-Token: my-secret-key')
        client_token = request.headers.get("X-Bootstrap-Token")
        hashed_cookie = jwt.encode({"key": client_token}, "admin_key", algorithm="HS256")
        return hashed_cookie == admin_token


class AuthViewSet(ViewSet):
    """User authentication endpoint handling cookies and session tracking."""

    permission_classes = [permissions.AllowAny]

    @action(
        detail=False,
        methods=["post"],
        url_path="register",
        permission_classes=[permissions.AllowAny],
    )
    def user_register(self, request):
        """Register a new user account in the system."""
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(role=user_db.Roles.USER)
            return Response(
                {"message": "User registered successfully"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["post"],
        url_path="create-tester",
        permission_classes=[permissions.IsAdminUser],
    )
    def create_test_user(self, request):
        """Create a test user account for development and testing purposes."""
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(role=user_db.Roles.TESTER)
            return Response(
                {"message": "Test account created successfully"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["post"],
        url_path="create-admin",
        permission_classes=[HasBootstrapToken],
    )
    def create_initial_admin(self, request):
        """Create an initial admin account."""
        serializer = CreateAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(role=user_db.Roles.ADMIN)
        return Response({"message": "Initial admin account created successfully"}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="create-admin", permission_classes=[permissions.IsAdminUser])
    def create_admins(self, request):
        """Create additional admin accounts."""
        serializer = CreateAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(role=user_db.Roles.ADMIN)
        return Response({"message": "Admin account created successfully"}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="login")
    def user_login(self, request):
        """Authenticate user credentials and set secure HTTP-only cookies."""
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assert serializer.validated_data is not None

        validated_data: dict[str, Any] = serializer.validated_data  # type: ignore[index]
        user = validated_data["user"]
        role = validated_data["role"]

        user_id = user.id

        refresh = RefreshToken.for_user(user)

        # pylint: disable=no-member
        user_session, created = session_db.objects.get_or_create(user_id=user_id, defaults={"session_version": 0})

        user_session.session_version = F("session_version") + 1
        user_session.save()

        user_session.session_token = str(refresh.access_token)
        user_session.last_ip = session_token.ip_address
        user_session.device_fingerprint = session_token.fingerprint
        user_session.payload_data = session_token(user_id, role, user_session.session_version, request)
        user_session.last_active = timezone.now()
        user_session.save()

        response = Response(
            {"user": UserLoginSerializer(user).data},
            status=status.HTTP_200_OK,
        )
        for key, val in [
            ("session_token", user_session.session_token),
            ("refresh_token", str(refresh)),
            ("fingerprint", user_session.device_fingerprint),
        ]:
            response.set_cookie(key=key, value=val, httponly=True, secure=True, samesite="Strict")

        return response

    @action(
        detail=False,
        methods=["post"],
        url_path="logout",
        permission_classes=[IsAuthenticated],
    )
    def user_logout(self, request):
        """Blacklist refresh token and nullify active user session database tracks."""
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            try:
                refresh = RefreshToken(refresh_token)
                refresh.blacklist()

                # pylint: disable=no-member
                user_session = session_db.objects.get(user_id=request.user.id)
                user_session.session_token = ""
                user_session.last_ip = ""
                user_session.session_version = 0
                user_session.payload_data = ""
                user_session.device_fingerprint = ""
                user_session.last_active = timezone.now()
                user_session.save()
            except TokenError:
                return Response(
                    {"error": "Refresh token not provided"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        response = Response({"message": "You have been logged out"}, status=status.HTTP_200_OK)
        for key in ["session_token", "refresh_token", "fingerprint"]:
            response.delete_cookie(key)
        return response

    @action(detail=False, methods=["post"], url_path="forgot-password", permission_classes=[permissions.AllowAny])
    def forgot_password(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_email = serializer.validated_data["email"]
