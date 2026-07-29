from dataclasses import dataclass

from memories.models import Logs


@dataclass
class ArticleContext:
    title: str
    description: str
    capsule_name: str
    language: str
    framework: str
    previous_articles: str | None


def generate_article_context(log_id: int) -> ArticleContext:
    log = Logs.objects.select_related("capsule", "creator").get(id=log_id)

    return ArticleContext(
        title=log.title,
        description=log.description,
        capsule_name=log.capsule.name,
        language=log.code_language,
        framework=log.code_framework,
        previous_articles=log.capsule.previous_articles,
    )
