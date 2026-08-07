from celery import shared_task

from memories.models import Logs


@shared_task
def queue_logs(log_payload):
    """
    Backwards-compatible task for older imports.

    New article generation is handled by inference.tasks and Celery Beat.
    """

    log_id = log_payload["log_id"]
    log_capsule = Logs.objects.select_related("capsule", "creator").get(id=log_id)
    return log_capsule
