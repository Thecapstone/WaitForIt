"""Serializers for user registration, authentication, and password management."""

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, Serializer

from authentication.models import User as user_db


class UserCreateSerializer(ModelSerializer):
    """Custom user creation serializer, validates input and hashes user password."""

    class Meta:
        model = user_db
        fields = ["email", "password"]
        extra_kwargs = {
            "email": {"required": True},
            "password": {"write_only": True, "required": True},
        }

    def create(self, validated_data):
        """Create a new user instance securely with a hashed password."""
        # Django's create_user automatically hashes the password!
        # pylint: disable=no-member
        # Standard fallback if using email as username
        user = user_db.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            is_active=False,
        )
        token = default_token_generator.make_token(user.email)

        # Send Email
        verification_link = f"http://localhost:8000/authentication/verify/{user.id}/{token}/"
        send_mail(
            subject="Verify your account",
            message=f"Click the link to verify: {verification_link}",
            from_email="noreply@yourdomain.com",
            recipient_list=[user.email],
        )
        return user


class CreateAdminSerializer(ModelSerializer):
    """Custom user creation serializer, validates input and hashes user password."""

    class Meta:
        model = user_db
        fields = ["email", "password"]
        extra_kwargs = {
            "email": {"required": True},
            "password": {"write_only": True, "required": True},
        }

    def create(self, validated_data):
        """Create a new user instance securely with a hashed password."""
        # Django's create_user automatically hashes the password!
        # pylint: disable=no-member
        # Standard fallback if using email as username
        user = user_db.objects.create_superuser(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            is_staff=True,
            is_superuser=True,
        )
        return user


class UserLoginSerializer(Serializer):
    """User login serializer, validates user active status."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Authenticate user credentials against the Django backend."""
        user = authenticate(username=attrs["email"], password=attrs["password"])
        if user and user.is_active:
            attrs["user"] = user
            return attrs
        raise serializers.ValidationError("Invalid credentials")


class EmailVerificationSerializer(Serializer):
    """Serializer for email verification, validates the provided token."""

    token = serializers.CharField(max_length=555)


class ForgotPasswordSerializer(Serializer):
    """Serializer for handling password reset requests."""

    email = serializers.EmailField(required=True)


# pylint: disable=too-few-public-methods
class PasswordResetSerializer(Serializer):
    """Serializer managing incoming email and credential updates."""

    email = serializers.EmailField(required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    new_password_confirm = serializers.CharField(write_only=True, required=True)
