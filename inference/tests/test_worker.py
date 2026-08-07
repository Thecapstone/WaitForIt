from inference.redis_worker import Dispatcher


def test_deprecated_dispatcher_routes_log_created(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "inference.dispatcher.dispatch_log_created",
        lambda log_id: calls.append(log_id),
    )

    Dispatcher.handle({
        "event": "log.created",
        "log_id": "5",
    })

    assert calls == ["5"]
