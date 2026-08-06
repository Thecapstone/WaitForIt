# inference/responseprocessor.py

from dataclasses import dataclass


@dataclass(slots=True)
class ArticleResponse:
    """
    Normalized article response extracted from an OpenRouter response.
    """

    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    finish_reason: str | None = None
    model: str | None = None


class ResponseProcessor:
    """
    Converts raw OpenRouter responses into strongly typed application objects.
    """

    @staticmethod
    def article(response: dict) -> ArticleResponse:
        """
        Normalize an article generation response.

        Parameters
        ----------
        response:
            Raw JSON returned by OpenRouter.

        Returns
        -------
        ArticleResponse

        Raises
        ------
        ValueError
            If the response is malformed.
        """

        try:
            choices = response["choices"]
        except KeyError as exc:
            raise ValueError("Response does not contain 'choices'.") from exc

        if not choices:
            raise ValueError("Response contains no choices.")

        choice = choices[0]

        message = choice.get("message")

        if not message:
            raise ValueError("Choice does not contain a message.")

        content = message.get("content")

        if content is None:
            raise ValueError("Choice message does not contain content.")

        if not isinstance(content, str):
            raise ValueError("Response content must be a string.")

        usage = response.get("usage", {})

        return ArticleResponse(
            content=content.strip(),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            total_tokens=int(usage.get("total_tokens", 0)),
            finish_reason=choice.get("finish_reason"),
            model=response.get("model"),
        )
