"""Authentication views handling user registration, login, and logout."""

import datetime
from datetime import timedelta
from tokenize import TokenError
from typing import Any

from django.db.models import F
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import (
    PasswordResetToken,
    Sessions as session_db,
    User as user_db,
)
from authentication.serializers import (
    CreateAdminSerializer,
    ForgotPasswordSerializer,
    PasswordResetSerializer,
    UserCreateSerializer,
    UserLoginSerializer,
)
from authentication.tokens import (
    HasBootstrapToken,
    TokenTypes,
    access_token,
    generate_password_reset_token,
    generate_token,
    session_token,
    verify_password_reset_token,
    verify_verification_token,
)
from helpers.emailClient import send_password_reset_email, send_verification_email


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
            user = request.user
            token_expiry = datetime.utcnow() + timedelta(hours=24)
            token = generate_token(
                user.id, token_expiry, token_type=TokenTypes["EMAIL"]
            )

        # Send Email
        verification_link = f"http://localhost:8000/auth/verify/{user.id}/{token}/"
        send_verification_email(
            receiver_email=user.email,
            verification_link=verification_link,
            verification_token=token,
        )

        is_verified = verify_verification_token(token)
        if is_verified:
            user.is_verified = True
            user.save()
            serializer.save(role=user_db.Roles.USER)
            return Response(
                {"message": "User registered successfully"},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            "Email verification failed. Please try again.",
            status=status.HTTP_404_NOT_FOUND,
        )

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
        return Response(
            {"message": "Initial admin account created successfully"},
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="create-admin",
        permission_classes=[permissions.IsAdminUser],
    )
    def create_admins(self, request):
        """Create additional admin accounts."""
        serializer = CreateAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(role=user_db.Roles.ADMIN)
        return Response(
            {"message": "Admin account created successfully"},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="login")
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
                {
                    "error": "Email not verified. Please verify your email before logging in."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # pylint: disable=no-member
        user_session, _created = session_db.objects.get_or_create(
            user_id=user, defaults={"session_version": 0}
        )

        refresh = session_token(user, role, user_session.session_version, request)
        access = access_token(refresh)
        user_session.session_version = F("session_version") + 1
        user_session.save()

        user_session.session_token = refresh
        user_session.last_ip = session_token.ip_address
        user_session.access_token = access
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
            response.set_cookie(
                key=key, value=val, httponly=True, secure=True, samesite="Strict"
            )

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
                user.is_active = False
                user.save()

                # pylint: disable=no-member
                user_session = session_db.objects.get(user_id=user.id)
                user_session.session_token = ""
                user_session.access_token = ""
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

        response = Response(
            {"message": "You have been logged out"}, status=status.HTTP_200_OK
        )
        for key in ["session_token", "refresh_token", "fingerprint"]:
            response.delete_cookie(key)
        return response

    @action(
        detail=False,
        methods=["post"],
        url_path="forgot-password",
        permission_classes=[permissions.AllowAny],
    )
    def forgot_password(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        user = user_db.objects.filter(email=email).first()

        if user:
            token_expiry = datetime.utcnow() + timedelta(minutes=30)
            token = generate_password_reset_token(
                user, token_expiry, token_type=TokenTypes["PASSWORD"]
            )

            reset_link = f"https://localhost:8000/auth/reset-password?token={token}"

            send_password_reset_email(
                user.email,
                reset_link,
                token,
            )

        return Response({
            "message": (
                "If an account exists with this email, "
                "a password reset link has been sent."
            )
        })

    @action(
        detail=True,
        methods=["post"],
        url_path="reset-password",
        permission_classes=[permissions.AllowAny],
    )
    def password_reset(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = verify_password_reset_token(serializer.validated_data["token"])

        user.set_password(serializer.validated_data["password"])
        user.session_version += 1
        user.save(update_fields=["password", "session_version"])

        # Invalidate every outstanding reset token for this user
        PasswordResetToken.objects.filter(user=user).delete()

        return Response({"message": "Password reset successful."})
