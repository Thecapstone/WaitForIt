import logging

from celery.exceptions import CeleryError
from django.db import transaction
from kombu.exceptions import OperationalError as KombuOperationalError

logger = logging.getLogger("waitforit")


def dispatch_log_created(log_id: str) -> None:
    """
    Register a newly created log for the daily Celery aggregation workflow.
    """

    from inference.tasks import queue_log_for_daily_article

    def enqueue_log() -> None:
        try:
            queue_log_for_daily_article.delay(str(log_id))
        except (CeleryError, KombuOperationalError) as exc:
            logger.warning(
                "LOG_ARTICLE_QUEUE_DISPATCH_FAILED | log=%s | error=%s",
                log_id,
                exc,
            )

    transaction.on_commit(enqueue_log)
