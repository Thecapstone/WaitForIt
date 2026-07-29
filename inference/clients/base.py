import os

from helpers.redisClient import STREAM, redis_client
from inference.clients.openRouter import OpenRouterClient
from inference.context import generate_article_context
from inference.promptBuilder import PromptBuilder
from inference.responseProcessor import ResponseProcessor
from inference.systemPrompt import system_prompt
from memories.models import Articles

ai_model = os.getenv("DEFAULT_MODEL")
model_temperature = os.getenv("TEMPERATURE")
max_tokens = os.getenv("MAX_TOKENS")


class InferenceService:
    @staticmethod
    def generate_article(log_id):
        context = generate_article_context(log_id)

        system = system_prompt(context.previous_articles)

        user = PromptBuilder.article(context)

        response = OpenRouterClient.generate(
            system_prompt=system,
            prompt=user,
            model=ai_model,
            temperature=model_temperature,
            max_tokens=max_tokens,
        )

        article = ResponseProcessor.article(response)

        Articles.objects.create(...)

        redis_client.xadd(
            STREAM,
            {
                "event": "article.generated",
                "article_id": article.id,
            },
        )
