"""Authentication views handling user registration, login, and logout."""
from tokenize import TokenError
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import F
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.tokens import RefreshToken


from authentication.models import Sessions as session_db
from authentication.models import User as user_db
from authentication.serializers import (
    CreateAdminSerializer,
    ForgotPasswordSerializer,
    PasswordResetSerializer,
    UserCreateSerializer,
    UserLoginSerializer,
    verify_verification_token,
)
from authentication.tokens import session_token, access_token, HasBootstrapToken


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

    @action(
        detail=True, 
        methods=["post"], 
        url_path="create-admin", 
        permission_classes=[permissions.IsAdminUser]
    )
    def create_admins(self, request):
        """Create additional admin accounts."""
        serializer = CreateAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(role=user_db.Roles.ADMIN)
        return Response({"message": "Admin account created successfully"}, status=status.HTTP_201_CREATED)

    @action(
        detail=False, 
        methods=["post"], 
        url_path="login"
    )
    def user_login(self, request):
        """Authenticate user credentials and set secure HTTP-only cookies."""
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data: dict[str, Any] = serializer.validated_data  # type: ignore[index]
        user = validated_data["user"]
        role = validated_data["role"]

        user = user.id
        user.is_active = True
        user.save()

        if not user.is_verified:
            return Response(
                {"error": "Email not verified. Please verify your email before logging in."},
                status=status.HTTP_403_FORBIDDEN,
            )
        refresh = session_token(user, role, user_session.session_version, request)

        # pylint: disable=no-member
        user_session, created = session_db.objects.get_or_create(user_id=user, defaults={"session_version": 0})

        user_session.session_version = F("session_version") + 1
        user_session.save()

        user_session.session_token = refresh
        user_session.last_ip = session_token.ip_address
        user_session.device_fingerprint = session_token.fingerprint
        user_session.payload_data = refresh.payload
        user_session.last_active = timezone.now()
        user_session.save()

        response = Response(
            {"user": UserLoginSerializer(user).data},
            status=status.HTTP_200_OK,
        )
        for key, val in [
            ("access_token", access_token),
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

                user = request.user
                user.is_active=False
                user.save()

                # pylint: disable=no-member
                user_session = session_db.objects.get(user_id=user.id)
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

    @action(
        detail=False, 
        methods=["post"], 
        url_path="forgot-password", 
        permission_classes=[permissions.AllowAny]
    )
    def forgot_password(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if verify_verification_token(serializer.token):
            user=request.user
            return user
        return Response("Account could not verified, please use a valid email")


    @action(
        detail=True,
        methods=["post"],
        url_path="reset-password",
        permission_classes=[permissions.IsAuthenticated]
    )
    def password_reset(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            user_id = request.user.id
            user = user_db.objects.get(id=user_id)
            user.get(password)