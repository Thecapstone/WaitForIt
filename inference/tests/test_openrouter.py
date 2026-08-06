import pytest

from inference.clients.openRouter import OpenRouterClient


@pytest.mark.asyncio
async def test_generate_posts_to_openrouter(mocker):
    fake_response = mocker.AsyncMock()

    fake_response.json.return_value = {"choices": []}
    fake_response.raise_for_status.return_value = None

    post = mocker.AsyncMock(return_value=fake_response)

    mock_client = mocker.AsyncMock()
    mock_client.post = post

    mocker.patch(
        "httpx.AsyncClient",
        return_value=mocker.AsyncMock(
            __aenter__=mocker.AsyncMock(return_value=mock_client),
            __aexit__=mocker.AsyncMock(return_value=None),
        ),
    )

    client = OpenRouterClient()

    await client.generate(
        system_prompt="system",
        prompt="user",
        model="gpt",
        temperature=0.7,
        max_tokens=500,
    )

    post.assert_called_once()
