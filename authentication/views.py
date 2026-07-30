"""Authentication views handling user registration, login, and logout."""

from datetime import timedelta
import hashlib
import os
from tokenize import TokenError
from typing import Any
from uuid import uuid4

from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from ipware import get_client_ip
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
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
    session_token,
    verify_password_reset_token,
    verify_verification_token,
)
from helpers.emailClient import send_password_reset_email, send_user_verification_email

Host = os.getenv("HOST")


class AuthViewSet(GenericViewSet):
    """User authentication endpoint handling cookies and session tracking."""

    def get_serializer_class(self):
        if self.action == "register_user":
            return UserCreateSerializer
        elif self.action == "create_initial_admin":
            return CreateAdminSerializer
        elif self.action == "create_admins":
            return CreateAdminSerializer
        elif self.action == "user_login":
            return UserLoginSerializer
        elif self.action == "forgot_password":
            return ForgotPasswordSerializer
        elif self.action == "password_reset":
            return PasswordResetSerializer

        return UserCreateSerializer

    # permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=UserCreateSerializer,
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                description="Register custom user."
            ),
        },
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path="register",
        permission_classes=[permissions.AllowAny],
    )
    def register_user(self, request):
        """Register a new user account in the system."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save(role=user_db.Roles.USER)
        success = send_user_verification_email(user)

        if not success:
            user.delete()
            # except Exception:
            return Response(
                {"message": "Unable to complete registration at this time."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": "Registration successful. Please check your email to verify your account."
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["GET"],
        url_path=r"verify/(?P<token>[^/]+)",
        permission_classes=[permissions.AllowAny],
    )
    def verify(self, request, token: str):
        """Verify a user's email address."""

        try:
            payload = verify_verification_token(token)
        except ValueError as exc:
            return Response(
                {"message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = get_object_or_404(
            user_db,
            id=payload["user_id"],
        )

        if user.is_verified:
            return Response(
                {"message": "Email is already verified."},
                status=status.HTTP_200_OK,
            )

        user.is_verified = True
        user.is_active = True
        user.save(update_fields=["is_verified", "is_active"])

        return Response(
            {"message": "Email verified successfully."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=UserCreateSerializer,
        responses={
            status.HTTP_200_OK: UserLoginSerializer,
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="create-tester",
        permission_classes=[permissions.IsAdminUser],
    )
    def create_test_user(self, request):
        """Create a test user account for development and testing purposes."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save(role=user_db.Roles.TESTER)
            user.is_verified = True
            user.save(update_fields=["is_verified"])
            return Response(
                {"message": "Test account created successfully"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["POST"],
        url_path="create-super-admin",
        permission_classes=[HasBootstrapToken],
    )
    def create_initial_admin(self, request):
        """Create an initial admin account."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(role=user_db.Roles.ADMIN)
        return Response(
            {"message": "Initial admin account created successfully"},
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["POST"],
        url_path="create-admin",
        permission_classes=[permissions.IsAdminUser],
    )
    def create_admins(self, request):
        """Create additional admin accounts."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(role=user_db.Roles.ADMIN)
        return Response(
            {"message": "Admin account created successfully"},
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["POST"],
        url_path="login",
        permission_classes=[permissions.AllowAny],
    )
    def user_login(self, request):
        """Authenticate user credentials and set secure HTTP-only cookies."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data: dict[str, Any] = serializer.validated_data  # type: ignore[index]
        user = validated_data["user"]
        role = user.role

        user.is_active = True
        user.save()

        if not user.is_verified:
            can_send = (
                not user.verification_email_sent_at
                or timezone.now() - user.verification_email_sent_at
                > timedelta(minutes=5)
            )

            if can_send:
                send_user_verification_email(user)

                user.verification_email_sent_at = timezone.now()
                user.save(update_fields=["verification_email_sent_at"])

                return Response(
                    {
                        "message": (
                            "Your email has not been verified. "
                            "We've sent you a new verification email."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            return Response(
                {
                    "message": (
                        "Your email has not been verified. "
                        "A verification email was sent recently. "
                        "Please wait a few minutes before requesting another."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        ip_address, _ = get_client_ip(request)
        fingerprint = hashlib.sha256(uuid4().bytes).hexdigest()
        user.last_login_ip = ip_address
        user.last_login = timezone.now()  # optional if you're tracking it
        user.save(update_fields=["last_login_ip", "last_login"])

        # pylint: disable=no-member
        user_session, _created = session_db.objects.get_or_create(
            user_id=user, defaults={"session_version": 0}
        )

        user_session.session_version = F("session_version") + 1
        user_session.save(update_fields=["session_version"])
        refresh = session_token(user.pk, role, user_session.session_version, request)
        access_token(refresh)

        user_session.session_token = refresh
        user_session.device_fingerprint = fingerprint
        user_session.last_ip = ip_address
        user_session.last_active = timezone.now()
        user_session.save(
            update_fields=[
                "session_token",
                "device_fingerprint",
                "last_ip",
                "last_active",
            ]
        )

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
        methods=["GET"],
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
                user.is_authenticated = False
                user.save()

                # pylint: disable=no-member
                user_session = session_db.objects.get(user_id=user.id)
                user_session.session_token = ""
                user_session.last_ip = ""
                user_session.session_version += 1
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

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={
            status.HTTP_200_OK: None,
        },
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path="forgot-password",
        permission_classes=[permissions.AllowAny],
    )
    def forgot_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = user_db.objects.filter(email=serializer.validated_data["email"]).first()

        if user:
            expiry = timezone.now() + timedelta(minutes=30)

            token = generate_password_reset_token(
                user.pk,
                expiry,
                token_type=TokenTypes["PASSWORD"],
            )
            reset_link = f"{Host}:8000/api/auth/password-reset/{token}/"

            try:
                send_password_reset_email(
                    user.email,
                    reset_link,
                    token,
                )
            except Exception:
                # Log only.
                pass

        return Response({
            "message": (
                "If an account exists with this email, "
                "a password reset link has been sent."
            )
        })

    @extend_schema(
        request=PasswordResetSerializer,
        responses={
            status.HTTP_200_OK: None,
            status.HTTP_400_BAD_REQUEST: None,
        },
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path=r"password-reset/(?P<token>[^/]+)",
        permission_classes=[permissions.AllowAny],
    )
    def password_reset(self, request, token=None):
        """Reset a user's password using a valid password reset token."""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = verify_password_reset_token(token)
        except ValueError as exc:
            return Response(
                {"message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = get_object_or_404(
            user_db,
            pk=payload["user_id"],
        )

        # Ensure the token hasn't already been used or revoked
        try:
            PasswordResetToken.objects.get(
                user=user,
                jti=payload["jti"],
            )
        except PasswordResetToken.DoesNotExist:
            return Response(
                {
                    "message": "Password reset token is invalid or has already been used."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])

        # Invalidate only the token that was used
        PasswordResetToken.objects.filter(
            jti=payload["jti"],
        ).delete()

        return Response(
            {"message": "Password reset successful."},
            status=status.HTTP_200_OK,
        )
