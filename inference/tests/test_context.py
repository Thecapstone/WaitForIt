import pytest

from inference.context import generate_article_context


@pytest.mark.django_db
def test_generate_article_context(log):
    context = generate_article_context(log.id)

    assert context.title == log.title
    assert context.description == log.description
    assert context.language == log.code_language
    assert context.framework == log.code_framework
    assert context.capsule_name == log.capsule.name
