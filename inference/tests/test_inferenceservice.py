from unittest.mock import AsyncMock

import pytest

from authentication.models import User
from inference.clients.base import InferenceService
from inference.responseProcessor import ArticleResponse
from memories.models import Articles, Capsule, Logs, Tag

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="developer@example.com", password="password")


@pytest.fixture
def capsule(user):
    return Capsule.objects.create(title="WaitForIt", creator=user)


@pytest.fixture
def logs(capsule, user):
    return [
        Logs.objects.create(
            capsule=capsule,
            creator=user,
            stamp="one",
            title="Implemented JWT",
            description="Added JWT authentication.",
            code_language="Python",
            code_framework="Django",
        ),
        Logs.objects.create(
            capsule=capsule,
            creator=user,
            stamp="two",
            title="Added refresh tokens",
            description="Rotated refresh tokens.",
            code_language="Python",
            code_framework="Django",
        ),
    ]


def test_generate_article_sync_creates_one_article_for_log_batch(
    monkeypatch,
    logs,
    capsule,
):
    monkeypatch.setattr(
        "inference.clients.base.OpenRouterClient.generate",
        AsyncMock(
            return_value={
                "choices": [
                    {"message": {"content": "Article"}, "finish_reason": "stop"}
                ]
            }
        ),
    )
    monkeypatch.setattr(
        "inference.clients.base.ResponseProcessor.article",
        lambda response: ArticleResponse(
            content="Generated article",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            finish_reason="stop",
            model="test-model",
        ),
    )

    article = InferenceService.generate_article_sync(logs)

    assert article == Articles.objects.get()
    assert article.capsule_id == capsule
    assert article.log == logs[0]
    assert set(article.logs.all()) == set(logs)
    assert article.body == "Generated article"
    assert article.tags == Tag.objects.get(name="daily-development")
    capsule.refresh_from_db()
    assert capsule.previous_article == "Generated article"
