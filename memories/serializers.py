from datetime import datetime
import logging
import os

from django.db import transaction
from rest_framework import serializers

# from helpers import STREAM, redis_client
from helpers.cloudinaryUtils import (
    _cleanup_cloudinary_resources,
    _generate_teaser_file,
    _save_upload_to_temp,
    _upload_cloudinary_resource,
    get_default_expiry,
)
from inference.dispatcher import dispatch_log_created
from memories.models import Capsule, Images, Logs, Teasers, Videos

logger = logging.getLogger("waitforit")


class CapsuleCreationSerializer(serializers.ModelSerializer):
    private = serializers.BooleanField(
        default=True, help_text="Restrict other users from view this profile"
    )
    maturity_date = serializers.DateTimeField(
        default=get_default_expiry, help_text="Time to open capsule"
    )
    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Capsule
        fields = [
            "title",
            "description",
            "creator",
            "previous_article",
            "maturity_date",
            "private",
        ]


class LogCreationSerializer(serializers.ModelSerializer):
    video = serializers.FileField(write_only=True, required=False)
    image = serializers.FileField(write_only=True, required=False)
    teasers = serializers.BooleanField(write_only=True, required=False, default=False)
    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())
    capsule = serializers.PrimaryKeyRelatedField(read_only=True)
    code_language = serializers.CharField(write_only=True)
    code_framework = serializers.CharField(write_only=True)

    class Meta:
        model = Logs
        fields = [
            "title",
            "description",
            "creator",
            "capsule",
            "code_language",
            "code_framework",
            "video",
            "image",
            "teasers",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else validated_data.get("creator")

        video_file = validated_data.pop("video", None)
        image_file = validated_data.pop("image", None)
        context = validated_data.pop("description", None)
        generate_teaser = validated_data.pop("teasers", False)

        uploaded_resources = []
        temp_paths = []

        with transaction.atomic():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_stamp = f"initial_log_{user.id}_{timestamp}"
            # image_link = cloudinary.utils.cloudinary_url("image_public_id")
            # video_link = cloudinary.utils.cloudinary_url("video_public_id")
            log = Logs.objects.create(
                stamp=log_stamp,
                description=context,
                title=validated_data["title"],
                capsule=validated_data["capsule"],
                creator=validated_data["creator"],
                code_language=validated_data.pop("code_language", ""),
                code_framework=validated_data.pop("code_framework", ""),
            )
            try:
                if video_file:
                    source_video_path = _save_upload_to_temp(video_file)
                    temp_paths.append(source_video_path)

                    video_upload = _upload_cloudinary_resource(
                        source_video_path,
                        resource_type="video",
                        folder="capsule_videos",
                    )
                    uploaded_resources.append({
                        "public_id": video_upload.get("public_id"),
                        "resource_type": "video",
                    })

                    video_url = video_upload.get("secure_url") or video_upload.get(
                        "url"
                    )
                    video_title = getattr(video_file, "name", "capsule_video")[:100]
                    video_obj = Videos.objects.create(
                        log=log,
                        capsule=log.capsule,
                        video_title=video_title,
                        video_file=video_url,
                        teaser=generate_teaser,
                    )

                    if generate_teaser:
                        teaser_path = _generate_teaser_file(source_video_path)
                        temp_paths.append(teaser_path)

                        teaser_upload = _upload_cloudinary_resource(
                            teaser_path, resource_type="video", folder="capsule_teasers"
                        )
                        uploaded_resources.append({
                            "public_id": teaser_upload.get("public_id"),
                            "resource_type": "video",
                        })

                        Teasers.objects.create(
                            video=video_obj,
                            teaser_url=teaser_upload.get("secure_url")
                            or teaser_upload.get("url"),
                        )

                if image_file:
                    source_image_path = _save_upload_to_temp(image_file)
                    temp_paths.append(source_image_path)

                    image_upload = _upload_cloudinary_resource(
                        source_image_path,
                        resource_type="image",
                        folder="capsule_images",
                    )
                    uploaded_resources.append({
                        "public_id": image_upload.get("public_id"),
                        "resource_type": "image",
                    })

                    image_url = image_upload.get("secure_url") or image_upload.get(
                        "url"
                    )
                    image_title = getattr(image_file, "name", "capsule_image")[:100]
                    Images.objects.create(
                        log=log,
                        capsule=log.capsule,
                        image_title=image_title,
                        image_file=image_url,
                    )

            except Exception as exc:
                _cleanup_cloudinary_resources(uploaded_resources)
                logger.warning(
                    "CLOUDINARY_RESOURCE_UPLOAD_FAILED | request=%s | error=%s ",
                    request.id,
                    exc,
                )
                raise exc

            finally:
                for temp_path in temp_paths:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            dispatch_log_created(log.id)
        return log


class CapsuleViewSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()

    def get_members(self, obj) -> int:
        return obj.member.count()

    class Meta:
        model = Capsule
        fields = [
            "title",
            "id",
            "members",
            "logs",
            "description",
            "created_at",
            "private",
        ]


class LogViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Logs
        fields = ["id", "title", "description", "created_at", "images", "videos"]


class CapsuleUpdateSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=224)
    description = serializers.CharField(max_length=220)

    class Meta:
        model = Capsule
        fields = ["title", "description"]


# class CapsulePreviewSerializer(serializers.ModelSerializer):
#     teasers = serializers.SerializerMethodField()

#     def get_teasers(self, obj):
#         return [
#             preview.teaser_url
#             for preview in obj.capsule_previews.all()
#             if preview.teaser_url
#         ]

#     def get(self, validated_data):
#         request = self.context.get("request")
#         capsule = request.capsule.id if request else None
#         Articles.objects.get(capsule=capsule)
#         Logs.objects.get(capsule=capsule)


# class CapsuleJoinSerializer(serializers.Serializer):
#     user_id = serializers.CharField()
#     capsule_id = serializers.CharField()
