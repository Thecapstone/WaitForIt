from unittest.mock import Mock

import pytest

from authentication.models import User
from inference.tasks import generate_daily_article_for_capsule
from memories.models import Capsule, Logs

pytestmark = pytest.mark.django_db


def test_daily_article_task_is_scheduled(settings):
    schedule = settings.CELERY_BEAT_SCHEDULE["generate-daily-articles"]

    assert schedule["task"] == "inference.tasks.generate_daily_articles"


def test_generate_daily_article_for_capsule_marks_logs_generated(monkeypatch):
    user = User.objects.create_user(email="developer@example.com", password="password")
    capsule = Capsule.objects.create(title="WaitForIt", creator=user)
    log = Logs.objects.create(
        capsule=capsule,
        creator=user,
        stamp="jwt",
        title="Implemented JWT",
        description="Added JWT auth.",
    )
    article = Mock(id="article-1")
    monkeypatch.setattr(
        "inference.tasks.InferenceService.generate_article_sync",
        lambda logs: article,
    )

    article_id = generate_daily_article_for_capsule(str(capsule.id))

    assert article_id == "article-1"
    log.refresh_from_db()
    assert log.is_generated is True
