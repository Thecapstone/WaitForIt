"""
Deprecated Redis worker entrypoint.

Article generation is now orchestrated by Celery tasks in ``inference.tasks``.
This module remains as a compatibility shim for old imports and should not be
used to trigger article generation.
"""


class ArticleWorker:
    @staticmethod
    def handle(payload):
        from inference.dispatcher import dispatch_log_created

        dispatch_log_created(payload["log_id"])


class Dispatcher:
    article_handlers = {
        "log.created": ArticleWorker.handle,
    }

    @classmethod
    def handle(cls, payload):
        handler = cls.article_handlers.get(payload["event"])

        if handler:
            handler(payload)

    @staticmethod
    def dispatch(payload):
        Dispatcher.handle(payload)
