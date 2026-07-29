from helpers.redisClient import redis_client

from .clients.base import BaseLLMClient

STREAM = "capsule.jobs"
GROUP = "article-workers"
CONSUMER = "worker-1"


class ArticleWorker:
    @staticmethod
    def handle(payload):
        log_id = int(payload["log_id"])

        BaseLLMClient.generate_article(log_id)


# class SummaryWorker:

#     @staticmethod
#     def handle(payload):

#         InferenceService.generate_summary(
#             payload["article_id"]
#         )


class Dispatcher:
    # summary_handlers = {
    #     "log.created": ArticleWorker.handle,
    #     "article.generated": SummaryWorker.handle,
    # }
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
        event = payload["event"]

        if event == "log.created":
            ...

        elif event == "article.generated":
            ...

        else:
            raise ValueError(event)


while True:
    messages = redis_client.xreadgroup(
        GROUP,
        CONSUMER,
        {STREAM: ">"},
        count=1,
        block=5000,
    )

    if not messages:
        continue

    stream_name, events = messages[0]

    message_id, payload = events[0]

    Dispatcher.dispatch(payload)

    print(payload)
