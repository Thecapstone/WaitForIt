from inference.context import ArticleContext
from inference.promptBuilder import PromptBuilder


def test_article_prompt_contains_context():
    context = ArticleContext(
        title="Redis Queue",
        description="Added Redis stream worker",
        capsule_name="WaitForIt",
        language="Python",
        framework="Django",
        previous_articles=None,
    )

    prompt = PromptBuilder.article(context)

    assert "Redis Queue" in prompt
    assert "Python" in prompt
    assert "Django" in prompt
    assert "WaitForIt" in prompt
