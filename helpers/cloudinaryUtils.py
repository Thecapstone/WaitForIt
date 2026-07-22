from datetime import timedelta
from pathlib import Path
import tempfile

from cloudinary.uploader import (
    destroy as delete_from_cloudinary,
    upload as upload_to_cloudinary,
)
from django.utils import timezone
import moviepy.Clip as VideoFileClip


def get_default_expiry():
    return timezone.now() + timedelta(days=1)


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
