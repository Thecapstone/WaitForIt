from datetime import datetime
from unittest.mock import MagicMock

from django.utils import timezone

from inference.context import ArticleContext
from inference.promptBuilder import PromptBuilder


def test_article_prompt_contains_aggregated_context():
    context = ArticleContext(
        title="WaitForIt daily development update",
        timeline="09:00\nImplemented JWT\nAdded login support",
        log_count=2,
        starts_at=timezone.make_aware(datetime(2026, 8, 6, 9, 0)),
        ends_at=timezone.make_aware(datetime(2026, 8, 6, 11, 30)),
        capsule=MagicMock(),
        capsule_name="WaitForIt",
        language="Python",
        framework="Django",
        project_metadata="Project: WaitForIt",
        capsule_metadata="Developer visibility",
        previous_articles=None,
        primary_log=MagicMock(),
        logs=(),
    )

    prompt = PromptBuilder.article(context)

    assert "Development Timeline" in prompt
    assert "Implemented JWT" in prompt
    assert "Log Count" in prompt
    assert "Python" in prompt
    assert "Django" in prompt
    assert "WaitForIt" in prompt
