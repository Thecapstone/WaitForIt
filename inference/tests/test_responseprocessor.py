from inference.responseProcessor import ResponseProcessor

response = {
    "model": "openai/gpt-4",
    "choices": [
        {
            "message": {"content": "Generated article"},
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 200,
        "total_tokens": 300,
    },
}


def test_article_response_processor():
    article = ResponseProcessor.article(response)

    assert article.content == "Generated article"
    assert article.prompt_tokens == 100
    assert article.total_tokens == 300
    assert article.finish_reason == "stop"
