from datetime import datetime
import json
import logging
import os
from pathlib import Path
import tempfile

from cloudinary.uploader import (
    destroy as delete_from_cloudinary,
    upload as upload_to_cloudinary,
)
import cloudinary.utils
from django.db import transaction
import moviepy.Clip as VideoFileClip
from rest_framework import serializers

from helpers import redisClient as _redis
from memories.models import Articles, Capsule, Images, Logs, Teasers, Videos

logger = logging.getLogger("waitforit")


def _save_upload_to_temp(uploaded_file):
    suffix = Path(getattr(uploaded_file, "name", "")).suffix or ".mp4"
    temp_file = tempfile.NamedTemporaryFile(
        prefix="capsule_upload_", suffix=suffix, delete=False
    )
    try:
        if hasattr(uploaded_file, "chunks"):
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
        else:
            temp_file.write(uploaded_file.read())
        temp_file.flush()
    finally:
        temp_file.close()

    return temp_file.name


def _upload_cloudinary_resource(source, resource_type="video", folder=None):
    options = {"resource_type": resource_type}
    if folder:
        options["folder"] = folder
    return upload_to_cloudinary(source, **options)


def _cleanup_cloudinary_resources(resources):
    for resource in resources:
        if isinstance(resource, dict):
            public_id = resource.get("public_id")
            resource_type = resource.get("resource_type")
        else:
            public_id = resource
            resource_type = None

        if public_id:
            delete_from_cloudinary(public_id, resource_type=resource_type)


def _get_teaser_window(duration_seconds):
    if duration_seconds <= 10:
        return 0, duration_seconds

    teaser_length = min(15, duration_seconds * 0.25)
    start = max(0, duration_seconds * 0.1)
    end = min(duration_seconds, start + teaser_length)
    return start, end


def _generate_teaser_file(video_path):
    teaser_suffix = Path(video_path).suffix or ".mp4"
    teaser_file = tempfile.NamedTemporaryFile(
        prefix="capsule_teaser_", suffix=teaser_suffix, delete=False
    )
    teaser_file_path = teaser_file.name
    teaser_file.close()

    with VideoFileClip(video_path) as clip:
        start, end = _get_teaser_window(clip.duration)
        clip.subclip(start, end).write_videofile(
            teaser_file_path,
            codec="libx264",
            audio_codec="aac",
            verbose=False,
            logger=None,
        )

    return teaser_file_path


class CapsuleCreationSerializer(serializers.ModelSerializer):
    video = serializers.FileField(write_only=True, required=False)
    image = serializers.FileField(write_only=True, required=False)
    teasers = serializers.BooleanField(write_only=True, required=False, default=False)
    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Capsule
        fields = [
            "title",
            "description",
            "creator",
            "log",
            "video",
            "image",
            "teasers",
            "private",
        ]

    async def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None

        video_file = validated_data.pop("video", None)
        image_file = validated_data.pop("image", None)
        log = validated_data.pop("log", None)
        generate_teaser = validated_data.pop("teasers", False)

        uploaded_resources = []
        temp_paths = []

        with transaction.atomic():
            image_link = cloudinary.utils.cloudinary_url("image_public_id")
            video_link = cloudinary.utils.cloudinary_url("video_public_id")
            capsule = Capsule.objects.create(image=image_link, video=video_link)
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
                        capsule=capsule,
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
                            capsule=capsule,
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
                        capsule=capsule, image_title=image_title, image_file=image_url
                    )
                if log:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    log_title = f"initial_log_{user.id}_{timestamp}"
                    Logs.objects.create(
                        capsule=capsule, title=log_title, description=log
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
            payload = {
                "capsule_id": capsule.id,
                "user_id": user.id,
                "log_id": log.id,
                "image_id": capsule.image.id if capsule.image else None,
            }
            await _redis.queue_log(
                json.dumps(payload),
            )
        return capsule


class CapsuleViewSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()

    def get_members(self, obj) -> int:
        return obj.member.count()

    class Meta:
        model = Capsule
        fields = ["title", "id", "members", "description", "created_at", "private"]


class CapsulePreviewSerializer(serializers.ModelSerializer):
    teasers = serializers.SerializerMethodField()

    def get_teasers(self, obj):
        return [
            preview.teaser_url
            for preview in obj.capsule_previews.all()
            if preview.teaser_url
        ]

    def get(self, validated_data):
        request = self.context.get("request")
        capsule = request.capsule.id if request else None
        Articles.objects.get(capsule=capsule)
        Logs.objects.get(capsule=capsule)

    class Meta:
        model = Capsule
        fields = ["title", "description", "teasers"]


class CapsuleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Capsule
        fields = ["image", "video", "teasers", "log"]

    async def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None

        video_file = validated_data.pop("video", None)
        image_file = validated_data.pop("image", None)
        log = validated_data("log", None)
        generate_teaser = validated_data.pop("teasers", False)

        uploaded_resources = []
        temp_paths = []

        with transaction.atomic():
            image_link = cloudinary.utils.cloudinary_url("image_public_id")
            video_link = cloudinary.utils.cloudinary_url("video_public_id")
            capsule = Capsule.objects.create(image=image_link, video=video_link)
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
                        capsule=capsule,
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
                            capsule=capsule,
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
                        capsule=capsule, image_title=image_title, image_file=image_url
                    )
                if log:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    log_title = f"new_log_{user.id}_{timestamp}"
                    Logs.objects.create(
                        capsule=capsule, title=log_title, description=log
                    )

            except Exception as e:
                _cleanup_cloudinary_resources(uploaded_resources)
                raise e
            finally:
                for temp_path in temp_paths:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            payload = {
                "capsule_id": capsule.id,
                "user_id": user.id,
                "log_id": log.id,
                "image_id": capsule.image.id if capsule.image else None,
            }
            await _redis.queue_log(
                json.dumps(payload),
            )
        return capsule


class CapsuleJoinSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    capsule_id = serializers.CharField()
