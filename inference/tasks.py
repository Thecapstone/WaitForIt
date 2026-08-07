from datetime import date

from celery import shared_task
from django.db import transaction

from inference.aggregation import daily_batches, logs_for_capsule_day
from inference.clients.base import InferenceService
from memories.models import Logs


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None

    return date.fromisoformat(value)


@shared_task
def queue_log_for_daily_article(log_id: str) -> dict:
    log = Logs.objects.select_related("capsule").get(id=log_id)

    return {
        "log_id": str(log.id),
        "capsule_id": str(log.capsule_id),
        "generation_date": log.created_at.date().isoformat(),
    }


@shared_task
def generate_daily_article_for_capsule(
    capsule_id: str,
    generation_date: str | None = None,
) -> str | None:
    target_day = _parse_date(generation_date)
    logs = tuple(logs_for_capsule_day(capsule_id, target_day))

    if not logs:
        return None

    with transaction.atomic():
        article = InferenceService.generate_article_sync(logs)
        Logs.objects.filter(id__in=[log.id for log in logs]).update(is_generated=True)

    return str(article.id)


@shared_task
def generate_daily_articles(generation_date: str | None = None) -> list[str]:
    target_day = _parse_date(generation_date)
    article_ids = []

    for batch in daily_batches(target_day):
        article_id = generate_daily_article_for_capsule(
            str(batch.capsule.id),
            generation_date,
        )

        if article_id:
            article_ids.append(article_id)

    return article_ids
