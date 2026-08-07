from unittest.mock import AsyncMock, Mock

from asgiref.sync import async_to_sync

from inference.clients.openRouter import OpenRouterClient


def test_generate_posts_to_openrouter(monkeypatch):
    fake_response = Mock()
    fake_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
    fake_response.raise_for_status.return_value = None

    post = AsyncMock(return_value=fake_response)

    mock_client = Mock()
    mock_client.post = post

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    client = OpenRouterClient()

    async_to_sync(client.generate)(
        system_prompt="system",
        prompt="user",
        model="gpt",
        temperature=0.7,
        max_tokens=500,
    )

    post.assert_called_once()
