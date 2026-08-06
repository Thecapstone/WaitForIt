import time

from celery import shared_task

from memories.models import Logs


@shared_task
def queue_logs(log_payload):
    log_id = log_payload["log_id"]
    log_capsule = Logs.objects.select_related("capsule", "creator").get(id=log_id)
    time.sleep(1200)
    return log_capsule
