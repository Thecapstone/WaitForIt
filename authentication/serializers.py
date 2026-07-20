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
from authentication.tokens import generate_token, verify_verification_token



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


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

# pylint: disable=too-few-public-methods
class PasswordResetSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                "Passwords do not match."
            )
        return attrs
