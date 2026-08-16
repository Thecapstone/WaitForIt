"""Serializers for user registration, authentication, and password management."""

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

    def validate_email(self, value):
        """Ensure the email address is unique."""
        if user_db.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        """Create a new user instance securely with a hashed password."""
        return user_db.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            is_active=False,
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
    """User login serializer, validates user credentials."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate user credentials."""

        email = attrs["email"].strip().lower()
        password = attrs["password"]

        try:
            user = user_db.objects.get(email=email)
        except user_db.DoesNotExist as exc:
            raise serializers.ValidationError("Invalid credentials") from exc

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials")

        attrs["user"] = user
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


# pylint: disable=too-few-public-methods
class PasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        return attrs
