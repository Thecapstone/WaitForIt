from collections.abc import Sequence
import os

from asgiref.sync import async_to_sync, sync_to_async

from inference.clients.openRouter import OpenRouterClient
from inference.context import generate_article_context
from inference.promptBuilder import PromptBuilder
from inference.responseProcessor import ResponseProcessor
from inference.systemPrompt import system_prompt
from memories.models import Articles, Logs, Tag

ai_model = os.getenv("DEFAULT_MODEL")
model_temperature = float(os.getenv("TEMPERATURE", "0.7"))
max_tokens = int(os.getenv("MAX_TOKENS", "4096"))


class InferenceService:
    """
    Coordinates article generation for an ordered batch of logs.

    Celery owns orchestration. This service only builds the context and prompt,
    calls the LLM client, processes the response, and saves the article.
    """

    @staticmethod
    def _generate_article(logs: Sequence[Logs] | Sequence[str]) -> Articles:
        """
        Generate one article from a developer-log batch.
        """

        context = generate_article_context(logs)

        system = system_prompt(context.previous_articles)
        prompt = PromptBuilder.article(context)
        client = OpenRouterClient()

        response = async_to_sync(client.generate)(
            system_prompt=system,
            prompt=prompt,
            model=ai_model,
            temperature=model_temperature,
            max_tokens=max_tokens,
        )

        article_response = ResponseProcessor.article(response)
        tag, _ = Tag.objects.get_or_create(name="daily-development")

        article = Articles.objects.create(
            capsule_id=context.capsule,
            log=context.primary_log,
            tags=tag,
            title=context.title[:120],
            body=article_response.content,
        )
        article.logs.set(context.logs)

        context.capsule.previous_article = article_response.content
        context.capsule.save(update_fields=["previous_article"])

        return article

    @staticmethod
    async def generate_article(logs: Sequence[Logs] | Sequence[str]) -> Articles:
        return await sync_to_async(InferenceService._generate_article)(logs)

    @staticmethod
    def generate_article_sync(logs: Sequence[Logs] | Sequence[str]) -> Articles:
        """
        Synchronous wrapper for Celery workers.
        """

        return InferenceService._generate_article(logs)
