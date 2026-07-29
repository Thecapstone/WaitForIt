from dataclasses import dataclass


@dataclass(slots=True)
class ArticleResponse:
    """
    Normalized response returned from the LLM.
    """

    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    finish_reason: str | None = None
    model: str | None = None


class ResponseProcessor:
    """
    Converts raw OpenRouter/OpenAI responses into application objects.
    """

    @staticmethod
    def article(response: dict) -> ArticleResponse:
        """
        Process an article generation response.
        """

        choice = response["choices"][0]
        usage = response.get("usage", {})

        return ArticleResponse(
            content=choice["message"]["content"].strip(),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            finish_reason=choice.get("finish_reason"),
            model=response.get("model"),
        )
