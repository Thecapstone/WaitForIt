# tests/memories/test_serializers.py


from django.core.files.uploadedfile import SimpleUploadedFile
import pytest
from rest_framework.test import APIRequestFactory

from authentication.models import User
from memories.models import Capsule
from memories.serializers import (
    CapsuleCreationSerializer,
    CapsuleUpdateSerializer,
    CapsuleViewSerializer,
    LogCreationSerializer,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def factory():
    return APIRequestFactory()


@pytest.fixture
def creator():
    return User.objects.create_user(
        email="creator@example.com",
        password="password123",
        first_name="John",
        last_name="Doe",
    )


@pytest.fixture
def capsule(creator):
    return Capsule.objects.create(
        title="Developer Journal",
        description="Building WaitForIt",
        creator=creator,
    )


@pytest.fixture
def serializer_context(factory, creator):
    request = factory.post("/")

    request.user = creator

    return {
        "request": request,
    }


@pytest.fixture
def image_file():
    return SimpleUploadedFile(
        "architecture.png",
        b"fake-image-content",
        content_type="image/png",
    )


@pytest.fixture
def video_file():
    return SimpleUploadedFile(
        "demo.mp4",
        b"fake-video-content",
        content_type="video/mp4",
    )


# ---------------------------------------------------------------------
# CapsuleCreationSerializer
# ---------------------------------------------------------------------


class TestCapsuleCreationSerializer:
    def test_serializer_is_valid(self, serializer_context):
        serializer = CapsuleCreationSerializer(
            data={
                "title": "My Capsule",
                "description": "Developer journey",
                "private": True,
            },
            context=serializer_context,
        )

        assert serializer.is_valid(), serializer.errors

    def test_create_capsule(self, serializer_context):
        serializer = CapsuleCreationSerializer(
            data={
                "title": "Redis Streams",
                "description": "Building background workers",
                "private": False,
            },
            context=serializer_context,
        )

        assert serializer.is_valid(), serializer.errors

        capsule = serializer.save()

        assert capsule.title == "Redis Streams"
        assert capsule.description == "Building background workers"
        assert capsule.creator == serializer_context["request"].user
        assert capsule.private is False

    def test_previous_article_defaults_blank(
        self,
        serializer_context,
    ):
        serializer = CapsuleCreationSerializer(
            data={
                "title": "Capsule",
                "description": "Description",
            },
            context=serializer_context,
        )

        assert serializer.is_valid(), serializer.errors

        capsule = serializer.save()

        assert capsule.previous_article == ""

    def test_title_required(self, serializer_context):
        serializer = CapsuleCreationSerializer(
            data={
                "description": "Missing title",
            },
            context=serializer_context,
        )

        assert serializer.is_valid() is False
        assert "title" in serializer.errors

    def test_creator_hidden_field(self, serializer_context):
        serializer = CapsuleCreationSerializer(
            data={
                "title": "Hidden User",
                "description": "Testing",
            },
            context=serializer_context,
        )

        assert serializer.is_valid(), serializer.errors

        capsule = serializer.save()

        assert capsule.creator == serializer_context["request"].user


# ---------------------------------------------------------------------
# CapsuleViewSerializer
# ---------------------------------------------------------------------


class TestCapsuleViewSerializer:
    def test_serialized_fields(self, capsule):
        data = CapsuleViewSerializer(capsule).data

        assert data["title"] == capsule.title
        assert data["description"] == capsule.description
        assert "id" in data
        assert "created_at" in data

    def test_member_count(self, capsule, creator):
        capsule.member.add(creator)

        data = CapsuleViewSerializer(capsule).data

        assert data["members"] == 1

    def test_multiple_members(self, capsule):
        user_one = User.objects.create_user(
            email="one@example.com",
            password="password123",
        )

        user_two = User.objects.create_user(
            email="two@example.com",
            password="password123",
        )

        capsule.member.add(user_one)
        capsule.member.add(user_two)

        data = CapsuleViewSerializer(capsule).data

        assert data["members"] == 2


# ---------------------------------------------------------------------
# CapsuleUpdateSerializer
# ---------------------------------------------------------------------


class TestCapsuleUpdateSerializer:
    def test_update_serializer_valid(self, capsule):
        serializer = CapsuleUpdateSerializer(
            capsule,
            data={
                "title": "Updated Title",
                "description": "Updated Description",
            },
        )

        assert serializer.is_valid(), serializer.errors

    def test_update_capsule(self, capsule):
        serializer = CapsuleUpdateSerializer(
            capsule,
            data={
                "title": "New Capsule",
                "description": "Updated",
            },
        )

        assert serializer.is_valid(), serializer.errors

        updated = serializer.save()

        assert updated.title == "New Capsule"
        assert updated.description == "Updated"

    def test_title_required(self, capsule):
        serializer = CapsuleUpdateSerializer(
            capsule,
            data={
                "description": "Only description",
            },
        )

        assert serializer.is_valid() is False
        assert "title" in serializer.errors

    def test_description_required(self, capsule):
        serializer = CapsuleUpdateSerializer(
            capsule,
            data={
                "title": "Only title",
            },
        )

        assert serializer.is_valid() is False
        assert "description" in serializer.errors


# ---------------------------------------------------------------------
# LogCreationSerializer Validation
# ---------------------------------------------------------------------


class TestLogCreationSerializerValidation:
    def test_serializer_valid(
        self,
        serializer_context,
    ):
        serializer = LogCreationSerializer(
            data={
                "title": "Redis Worker",
                "description": "Implemented worker",
                "code_language": "Python",
                "code_framework": "Django",
            },
            context=serializer_context,
        )

        assert serializer.is_valid(), serializer.errors

    def test_video_optional(
        self,
        serializer_context,
    ):
        serializer = LogCreationSerializer(
            data={
                "title": "Video Optional",
                "description": "Testing",
                "code_language": "Python",
                "code_framework": "FastAPI",
            },
            context=serializer_context,
        )

        assert serializer.is_valid(), serializer.errors

    def test_image_optional(
        self,
        serializer_context,
    ):
        serializer = LogCreationSerializer(
            data={
                "title": "Image Optional",
                "description": "Testing",
                "code_language": "Python",
                "code_framework": "FastAPI",
            },
            context=serializer_context,
        )

        assert serializer.is_valid(), serializer.errors

    def test_accepts_image_upload(
        self,
        serializer_context,
        image_file,
    ):
        serializer = LogCreationSerializer(
            data={
                "title": "Image",
                "description": "Testing upload",
                "code_language": "Python",
                "code_framework": "Django",
                "image": image_file,
            },
            context=serializer_context,
        )

        assert serializer.is_valid(), serializer.errors

    def test_accepts_video_upload(
        self,
        serializer_context,
        video_file,
    ):
        serializer = LogCreationSerializer(
            data={
                "title": "Video",
                "description": "Testing upload",
                "code_language": "Python",
                "code_framework": "Django",
                "video": video_file,
            },
            context=serializer_context,
        )

        assert serializer.is_valid(), serializer.errors

    def test_title_required(
        self,
        serializer_context,
    ):
        serializer = LogCreationSerializer(
            data={
                "description": "Missing title",
                "code_language": "Python",
                "code_framework": "Django",
            },
            context=serializer_context,
        )

        assert serializer.is_valid() is False
        assert "title" in serializer.errors

    def test_description_required(
        self,
        serializer_context,
    ):
        serializer = LogCreationSerializer(
            data={
                "title": "Missing description",
                "code_language": "Python",
                "code_framework": "Django",
            },
            context=serializer_context,
        )

        assert serializer.is_valid() is False
        assert "description" in serializer.errors

    def test_language_required(
        self,
        serializer_context,
    ):
        serializer = LogCreationSerializer(
            data={
                "title": "Language",
                "description": "Testing",
                "code_framework": "Django",
            },
            context=serializer_context,
        )

        assert serializer.is_valid() is False
        assert "code_language" in serializer.errors

    def test_framework_required(
        self,
        serializer_context,
    ):
        serializer = LogCreationSerializer(
            data={
                "title": "Framework",
                "description": "Testing",
                "code_language": "Python",
            },
            context=serializer_context,
        )

        assert serializer.is_valid() is False
        assert "code_framework" in serializer.errors

    def test_teasers_defaults_false(
        self,
        serializer_context,
    ):
        serializer = LogCreationSerializer(
            data={
                "title": "Teaser",
                "description": "Testing",
                "code_language": "Python",
                "code_framework": "Django",
            },
            context=serializer_context,
        )

        assert serializer.is_valid(), serializer.errors

        assert serializer.validated_data["teasers"] is False
