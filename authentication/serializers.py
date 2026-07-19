"""Serializers for user registration, authentication, and password management."""

import datetime
import os

import jwt
from datetime import timedelta
from helpers.emailClient import send_password_reset_email, send_verification_email
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, Serializer

from authentication.models import User as user_db

EMAIL_SECRET_KEY = os.getenv("Email_Key")
ALGORITHM = "HS256"

TokenTypes = {"EMAIL": "email_verification", "PASSWORD": "password_reset"}


def generate_token(user_id, token_type) -> str:
    """Generate a unique token for email verification."""
    payload = {
        "user_id": user_id,
        "type": token_type,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, EMAIL_SECRET_KEY, algorithm=ALGORITHM)


def verify_verification_token(token) -> str:
    """Verify user account using email token"""
    try:
        payload = jwt.decode(token, EMAIL_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "email_verification":
            raise serializers.ValidationError("Invalid token type.")
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise serializers.ValidationError("Token has expired.")
    except jwt.InvalidTokenError:
        raise serializers.ValidationError("Invalid token.")


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
        token = generate_token(user.id, token_type=TokenTypes["EMAIL"])

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
            return user
        return serializers.ValidationError(
            "Email verification failed. Please try again."
        )


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


class ForgotPasswordSerializer(Serializer):
    """Serializer for handling password reset requests."""

    email = serializers.EmailField(required=True)
    user = authenticate(email)
    token = generate_token(user.id, token_type=TokenTypes["PASSWORD"])

    password_reset_link = f"http://localhost:8000/auth/forgot-password/{token}/"
    send_password_reset_email(
        user=user.email, reset_link=password_reset_link, reset_token=token
    )


# pylint: disable=too-few-public-methods
class PasswordResetSerializer(Serializer):
    """Serializer managing incoming email and credential updates."""

    email = serializers.EmailField(required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    new_password_confirm = serializers.CharField(write_only=True, required=True)
