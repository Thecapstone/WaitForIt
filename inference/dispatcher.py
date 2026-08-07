from django.db import transaction


def dispatch_log_created(log_id: str) -> None:
    """
    Register a newly created log for the daily Celery aggregation workflow.
    """

    from inference.tasks import queue_log_for_daily_article

    transaction.on_commit(lambda: queue_log_for_daily_article.delay(str(log_id)))
