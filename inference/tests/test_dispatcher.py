from kombu.exceptions import OperationalError as KombuOperationalError

from inference.dispatcher import dispatch_log_created


def test_dispatch_log_created_does_not_fail_request_when_broker_is_down(
    db,
    django_capture_on_commit_callbacks,
    monkeypatch,
):
    def broker_down(_log_id):
        raise KombuOperationalError("broker unavailable")

    monkeypatch.setattr(
        "inference.tasks.queue_log_for_daily_article.delay",
        broker_down,
    )

    with django_capture_on_commit_callbacks(execute=True):
        dispatch_log_created("log-1")
