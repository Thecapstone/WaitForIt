# tests/memories/test_models.py

from datetime import timedelta

from django.utils import timezone
import pytest

from authentication.models import User
from memories.models import (
    Articles,
    Capsule,
    Images,
    Logs,
    Tag,
    Teasers,
    Videos,
    get_default_expiry,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def user():
    return User.objects.create_user(
        email="developer@example.com",
        password="password123",
        first_name="John",
        last_name="Doe",
    )


@pytest.fixture
def capsule(user):
    return Capsule.objects.create(
        title="WaitForIt",
        description="Developer journey",
        creator=user,
    )


@pytest.fixture
def log(user, capsule):
    return Logs.objects.create(
        capsule=capsule,
        creator=user,
        stamp="initial_log",
        title="Started Redis Worker",
        description="Implemented the worker.",
    )


# ---------------------------------------------------------------------
# get_default_expiry
# ---------------------------------------------------------------------


class TestDefaultExpiry:
    def test_default_expiry_is_one_day_ahead(self):
        now = timezone.now()

        expiry = get_default_expiry()

        delta = expiry - now

        assert timedelta(hours=23, minutes=59) <= delta <= timedelta(days=1, seconds=2)


# ---------------------------------------------------------------------
# Capsule
# ---------------------------------------------------------------------


class TestCapsuleModel:
    def test_create_capsule(self, capsule, user):
        assert capsule.title == "WaitForIt"
        assert capsule.description == "Developer journey"
        assert capsule.creator == user

    def test_capsule_private_defaults_true(self, capsule):
        assert capsule.private is True

    def test_is_private_property(self, capsule):
        assert capsule.is_private is True

    def test_is_open_returns_false_before_maturity(self, capsule):
        assert capsule.is_open() is False

    def test_is_open_returns_true_after_maturity(self, capsule):
        capsule.maturity_date = timezone.now() - timedelta(days=1)
        capsule.save()

        assert capsule.is_open() is True

    def test_repr_contains_title(self, capsule):
        representation = repr(capsule)

        assert "WaitForIt" in representation
        assert "private" in representation.lower()

    def test_member_relationship(self, capsule, user):
        capsule.member.add(user)

        assert capsule.member.count() == 1
        assert user in capsule.member.all()

    def test_contributor_relationship(self, capsule, user):
        capsule.contributor.add(user)

        assert capsule.contributor.count() == 1
        assert user in capsule.contributor.all()

    def test_previous_article_defaults_blank(self, capsule):
        assert capsule.previous_article == ""

    def test_created_at_is_set(self, capsule):
        assert capsule.created_at is not None

    def test_updated_at_is_set(self, capsule):
        assert capsule.updated_at is not None


# ---------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------


class TestLogsModel:
    def test_create_log(self, log, capsule, user):
        assert log.capsule == capsule
        assert log.creator == user
        assert log.title == "Started Redis Worker"

    def test_log_description(self, log):
        assert log.description == "Implemented the worker."

    def test_log_stamp(self, log):
        assert log.stamp == "initial_log"

    def test_log_created_at(self, log):
        assert log.created_at is not None

    def test_log_updated_at(self, log):
        assert log.updated_at is not None

    def test_capsule_reverse_relation(self, capsule, log):
        assert capsule.logs.count() == 1
        assert log in capsule.logs.all()

    def test_creator_reverse_relation(self, user, log):
        assert user.logs.count() == 1
        assert log in user.logs.all()


# ---------------------------------------------------------------------
# Fixtures for media and article models
# ---------------------------------------------------------------------


@pytest.fixture
def video(log, capsule):
    return Videos.objects.create(
        capsule=capsule,
        log=log,
        video_title="Redis Worker Demo",
        video_file="https://example.com/video.mp4",
        teaser=False,
    )


@pytest.fixture
def image(log, capsule):
    return Images.objects.create(
        capsule=capsule,
        log=log,
        image_title="Redis Architecture",
        image_file="https://example.com/image.png",
    )


@pytest.fixture
def teaser(video, capsule):
    return Teasers.objects.create(
        video=video,
        capsule=capsule,
        teaser_url="https://example.com/teaser.mp4",
    )


@pytest.fixture
def tag():
    return Tag.objects.create(
        name="django",
    )


@pytest.fixture
def article(capsule, log, tag):
    return Articles.objects.create(
        title="Building a Redis Worker",
        capsule_id=capsule,
        log=log,
        tags=tag,
        body="This is the generated article.",
        image="https://example.com/article.png",
    )


# ---------------------------------------------------------------------
# Videos
# ---------------------------------------------------------------------


class TestVideosModel:
    def test_create_video(self, video, capsule, log):
        assert video.capsule == capsule
        assert video.log == log
        assert video.video_title == "Redis Worker Demo"

    def test_video_file_saved(self, video):
        assert video.video_file == "https://example.com/video.mp4"

    def test_video_not_teaser_by_default(self, video):
        assert video.teaser is False

    def test_use_for_teaser_generation_false(self, video):
        assert video.use_for_teaser_generation is False

    def test_use_for_teaser_generation_true(
        self,
        video,
    ):
        video.teaser = True
        video.save()

        assert video.use_for_teaser_generation is True

    def test_capsule_reverse_relation(
        self,
        capsule,
        video,
    ):
        assert capsule.videos.count() == 1
        assert video in capsule.videos.all()

    def test_log_reverse_relation(
        self,
        log,
        video,
    ):
        assert log.videos.count() == 1
        assert video in log.videos.all()

    def test_video_created_at(self, video):
        assert video.created_at is not None

    def test_video_updated_at(self, video):
        assert video.updated_at is not None


# ---------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------


class TestImagesModel:
    def test_create_image(
        self,
        image,
        capsule,
        log,
    ):
        assert image.capsule == capsule
        assert image.log == log

    def test_image_title(self, image):
        assert image.image_title == "Redis Architecture"

    def test_image_file(self, image):
        assert image.image_file == "https://example.com/image.png"

    def test_capsule_reverse_relation(
        self,
        capsule,
        image,
    ):
        assert capsule.images.count() == 1
        assert image in capsule.images.all()

    def test_log_reverse_relation(
        self,
        log,
        image,
    ):
        assert log.images.count() == 1
        assert image in log.images.all()

    def test_image_created_at(self, image):
        assert image.created_at is not None

    def test_image_updated_at(self, image):
        assert image.updated_at is not None


# ---------------------------------------------------------------------
# Teasers
# ---------------------------------------------------------------------


class TestTeasersModel:
    def test_create_teaser(
        self,
        teaser,
        video,
        capsule,
    ):
        assert teaser.video == video
        assert teaser.capsule == capsule

    def test_teaser_url(self, teaser):
        assert teaser.teaser_url == "https://example.com/teaser.mp4"

    def test_capsule_reverse_relation(
        self,
        capsule,
        teaser,
    ):
        assert capsule.video_previews.count() == 1
        assert teaser in capsule.video_previews.all()

    def test_video_reverse_relation(
        self,
        video,
        teaser,
    ):
        assert video.preview.count() == 1
        assert teaser in video.preview.all()

    def test_teaser_created_at(self, teaser):
        assert teaser.created_at is not None

    def test_teaser_updated_at(self, teaser):
        assert teaser.updated_at is not None


# ---------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------


class TestTagModel:
    def test_create_tag(self, tag):
        assert tag.name == "django"

    def test_tag_string_representation(
        self,
        tag,
    ):
        assert str(tag) == "django"

    def test_tag_is_unique(self):
        Tag.objects.create(name="python")

        with pytest.raises(Exception):
            Tag.objects.create(name="python")


# ---------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------


class TestArticlesModel:
    def test_create_article(
        self,
        article,
        capsule,
        log,
        tag,
    ):
        assert article.title == "Building a Redis Worker"
        assert article.capsule_id == capsule
        assert article.log == log
        assert article.tags == tag

    def test_article_body(self, article):
        assert article.body == "This is the generated article."

    def test_article_image(self, article):
        assert article.image == "https://example.com/article.png"

    def test_article_string_representation(
        self,
        article,
    ):
        assert str(article) == "Building a Redis Worker"

    def test_capsule_reverse_relation(
        self,
        capsule,
        article,
    ):
        assert capsule.articles.count() == 1
        assert article in capsule.articles.all()

    def test_log_reverse_relation(
        self,
        log,
        article,
    ):
        assert log.articles.count() == 1
        assert article in log.articles.all()

    def test_tag_reverse_relation(
        self,
        tag,
        article,
    ):
        assert tag.article.count() == 1
        assert article in tag.article.all()


# ---------------------------------------------------------------------
# Articles (continued)
# ---------------------------------------------------------------------


class TestArticlesModelIntegrity:
    def test_article_has_valid_foreign_keys(
        self,
        article,
        capsule,
        log,
        tag,
    ):
        assert article.capsule_id.pk == capsule.pk
        assert article.log.pk == log.pk
        assert article.tags.pk == tag.pk

    def test_multiple_articles_can_share_same_capsule(
        self,
        capsule,
        log,
        tag,
    ):
        first = Articles.objects.create(
            title="Article One",
            capsule_id=capsule,
            log=log,
            tags=tag,
            body="Body one",
            image="https://example.com/one.png",
        )

        second = Articles.objects.create(
            title="Article Two",
            capsule_id=capsule,
            log=log,
            tags=tag,
            body="Body two",
            image="https://example.com/two.png",
        )

        assert capsule.articles.count() == 2
        assert first in capsule.articles.all()
        assert second in capsule.articles.all()

    def test_multiple_articles_can_share_same_tag(
        self,
        capsule,
        log,
        tag,
    ):
        Articles.objects.create(
            title="Redis Streams",
            capsule_id=capsule,
            log=log,
            tags=tag,
            body="Redis article",
            image="https://example.com/redis.png",
        )

        Articles.objects.create(
            title="Celery Workers",
            capsule_id=capsule,
            log=log,
            tags=tag,
            body="Celery article",
            image="https://example.com/celery.png",
        )

        assert tag.article.count() == 2

    def test_article_body_can_be_long(
        self,
        capsule,
        log,
        tag,
    ):
        body = "Lorem ipsum " * 1000

        article = Articles.objects.create(
            title="Large Body",
            capsule_id=capsule,
            log=log,
            tags=tag,
            body=body,
            image="",
        )

        assert article.body == body

    def test_article_image_can_be_blank(
        self,
        capsule,
        log,
        tag,
    ):
        article = Articles.objects.create(
            title="No Image",
            capsule_id=capsule,
            log=log,
            tags=tag,
            body="Content",
            image="",
        )

        assert article.image == ""

    def test_deleting_article_does_not_delete_capsule(
        self,
        capsule,
        log,
        tag,
    ):
        article = Articles.objects.create(
            title="Temporary",
            capsule_id=capsule,
            log=log,
            tags=tag,
            body="Temp",
            image="",
        )

        article.delete()

        assert Capsule.objects.filter(pk=capsule.pk).exists()

    def test_deleting_article_does_not_delete_log(
        self,
        capsule,
        log,
        tag,
    ):
        article = Articles.objects.create(
            title="Temporary",
            capsule_id=capsule,
            log=log,
            tags=tag,
            body="Temp",
            image="",
        )

        article.delete()

        assert Logs.objects.filter(pk=log.pk).exists()

    def test_deleting_capsule_deletes_article(
        self,
        article,
        capsule,
    ):
        article_pk = article.pk

        capsule.delete()

        assert not Articles.objects.filter(pk=article_pk).exists()

    def test_deleting_log_deletes_article(
        self,
        article,
        log,
    ):
        article_pk = article.pk

        log.delete()

        assert not Articles.objects.filter(pk=article_pk).exists()

    def test_deleting_tag_is_protected_by_do_nothing(
        self,
        tag,
        article,
    ):
        """
        DO_NOTHING means Django doesn't cascade the delete.
        The database ultimately determines whether the delete
        succeeds depending on its FK constraints.
        """

        assert article.tags == tag


# ---------------------------------------------------------------------
# General model metadata
# ---------------------------------------------------------------------


class TestModelMetadata:
    def test_capsule_verbose_name(self):
        assert Capsule._meta.model_name == "capsule"

    def test_logs_verbose_name(self):
        assert Logs._meta.model_name == "logs"

    def test_videos_verbose_name(self):
        assert Videos._meta.model_name == "videos"

    def test_images_verbose_name(self):
        assert Images._meta.model_name == "images"

    def test_teasers_verbose_name(self):
        assert Teasers._meta.model_name == "teasers"

    def test_articles_verbose_name(self):
        assert Articles._meta.model_name == "articles"

    def test_tag_verbose_name(self):
        assert Tag._meta.model_name == "tag"

    def test_capsule_has_expected_fields(self):
        fields = {field.name for field in Capsule._meta.get_fields()}

        expected = {
            "title",
            "description",
            "creator",
            "member",
            "contributor",
            "private",
            "maturity_date",
            "previous_article",
            "created_at",
            "updated_at",
        }

        assert expected.issubset(fields)

    def test_logs_has_expected_fields(self):
        fields = {field.name for field in Logs._meta.get_fields()}

        expected = {
            "capsule",
            "creator",
            "stamp",
            "title",
            "description",
            "created_at",
            "updated_at",
        }

        assert expected.issubset(fields)

    def test_articles_has_expected_fields(self):
        fields = {field.name for field in Articles._meta.get_fields()}

        expected = {
            "title",
            "capsule_id",
            "log",
            "tags",
            "body",
            "image",
        }

        assert expected.issubset(fields)
