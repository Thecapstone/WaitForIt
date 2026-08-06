from inference.redis_worker import Dispatcher


def test_dispatcher_calls_article_worker(mocker):
    worker = mocker.patch("inference.redis_worker.ArticleWorker.handle")

    Dispatcher.handle({
        "event": "log.created",
        "log_id": "5",
    })

    worker.assert_called_once()
