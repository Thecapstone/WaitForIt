import os

from asgiref.sync import async_to_sync

from helpers.redisClient import STREAM, redis_client
from inference.clients.openRouter import OpenRouterClient
from inference.context import generate_article_context
from inference.promptBuilder import PromptBuilder
from inference.responseProcessor import ResponseProcessor
from inference.systemPrompt import system_prompt
from memories.models import Articles

ai_model = os.getenv("DEFAULT_MODEL")
model_temperature = float(os.getenv("TEMPERATURE", "0.7"))
max_tokens = int(os.getenv("MAX_TOKENS", "4096"))


class InferenceService:
    """
    Coordinates the complete article generation pipeline.

    Flow

    Log
        ↓
    Context
        ↓
    Prompt Builder
        ↓
    OpenRouter
        ↓
    Response Processor
        ↓
    Save Article
        ↓
    Publish Redis Event
    """

    @staticmethod
    async def generate_article(log_id: int) -> Articles:
        """
        Generate an article from a developer log.

        Returns
        -------
        Articles
            The newly created Article instance.
        """

        context = generate_article_context(log_id)

        system = system_prompt(context.previous_articles)

        prompt = PromptBuilder.article(context)

        client = OpenRouterClient()

        response = await client.generate(
            system_prompt=system,
            prompt=prompt,
            model=ai_model,
            temperature=model_temperature,
            max_tokens=max_tokens,
        )

        article_response = ResponseProcessor.article(response)

        article = Articles.objects.create(
            capsule=context.capsule,
            title=context.title,
            content=article_response.content,
            prompt_tokens=article_response.prompt_tokens,
            completion_tokens=article_response.completion_tokens,
            total_tokens=article_response.total_tokens,
            finish_reason=article_response.finish_reason,
            model=article_response.model,
        )

        redis_client.xadd(
            STREAM,
            {
                "event": "article.generated",
                "article_id": str(article.id),
            },
        )

        return article

    @staticmethod
    def generate_article_sync(log_id: int) -> Articles:
        """
        Synchronous wrapper for Redis workers.
        """
        return async_to_sync(InferenceService.generate_article)(log_id)
