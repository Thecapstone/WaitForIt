# tests/inference/test_inference_service.py

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from inference.clients.base import InferenceService
from inference.context import ArticleContext
from inference.responseProcessor import ArticleResponse

pytestmark = pytest.mark.django_db


class TestInferenceService:
    @pytest.fixture
    def context(self):
        """
        Shared article context returned from generate_article_context().
        """
        capsule = MagicMock()
        capsule.id = 10
        capsule.name = "WaitForIt"

        return ArticleContext(
            title="Building a Redis Worker",
            description=(
                "Implemented a Redis stream worker that listens for newly created logs."
            ),
            capsule=capsule,
            capsule_name="WaitForIt",
            language="Python",
            framework="Django",
            previous_articles="Previous writing sample.",
        )

    @pytest.fixture
    def llm_response(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "# Building a Redis Worker\n\n"
                            "This article explains how the worker was built."
                        )
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 121,
                "completion_tokens": 504,
                "total_tokens": 625,
            },
            "model": "anthropic/claude-sonnet-4",
        }

    @pytest.fixture
    def processed_response(self):
        return ArticleResponse(
            content=(
                "# Building a Redis Worker\n\n"
                "This article explains how the worker was built."
            ),
            prompt_tokens=121,
            completion_tokens=504,
            total_tokens=625,
            finish_reason="stop",
            model="anthropic/claude-sonnet-4",
        )

    @pytest.fixture
    def saved_article(self):
        article = MagicMock()

        article.id = 44
        article.title = "Building a Redis Worker"

        return article

    @pytest.fixture
    def service_dependencies(
        self,
        mocker,
        context,
        llm_response,
        processed_response,
        saved_article,
    ):
        """
        Patch every external dependency used by
        InferenceService.generate_article().
        """

        generate_context = mocker.patch(
            "inference.clients.base.generate_article_context",
            return_value=context,
        )

        build_system_prompt = mocker.patch(
            "inference.clients.base.system_prompt",
            return_value="SYSTEM PROMPT",
        )

        build_user_prompt = mocker.patch(
            "inference.clients.base.PromptBuilder.article",
            return_value="USER PROMPT",
        )

        openrouter = mocker.patch(
            "inference.clients.base.OpenRouterClient.generate",
            new_callable=AsyncMock,
            return_value=llm_response,
        )

        processor = mocker.patch(
            "inference.clients.base.ResponseProcessor.article",
            return_value=processed_response,
        )

        create_article = mocker.patch(
            "inference.clients.base.Articles.objects.create",
            return_value=saved_article,
        )

        redis = mocker.patch("inference.clients.base.redis_client.xadd")

        return SimpleNamespace(
            generate_context=generate_context,
            build_system_prompt=build_system_prompt,
            build_user_prompt=build_user_prompt,
            openrouter=openrouter,
            processor=processor,
            create_article=create_article,
            redis=redis,
        )

    @pytest.mark.asyncio
    async def test_generate_article_returns_created_article(
        self,
        saved_article,
        service_dependencies,
    ):
        article = await InferenceService.generate_article(8)

        assert article is saved_article

    @pytest.mark.asyncio
    async def test_context_is_generated(
        self,
        service_dependencies,
    ):
        await InferenceService.generate_article(55)

        service_dependencies.generate_context.assert_called_once_with(55)

    @pytest.mark.asyncio
    async def test_system_prompt_is_generated_from_previous_articles(
        self,
        context,
        service_dependencies,
    ):
        await InferenceService.generate_article(1)

        service_dependencies.build_system_prompt.assert_called_once_with(
            context.previous_articles
        )

    @pytest.mark.asyncio
    async def test_user_prompt_is_generated(
        self,
        context,
        service_dependencies,
    ):
        await InferenceService.generate_article(2)

        service_dependencies.build_user_prompt.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_openrouter_called_with_expected_arguments(
        self,
        service_dependencies,
    ):
        await InferenceService.generate_article(3)

        kwargs = service_dependencies.openrouter.await_args.kwargs

        assert kwargs["system_prompt"] == "SYSTEM PROMPT"
        assert kwargs["prompt"] == "USER PROMPT"

        assert "model" in kwargs
        assert "temperature" in kwargs
        assert "max_tokens" in kwargs

    @pytest.mark.asyncio
    async def test_response_processor_receives_raw_response(
        self,
        llm_response,
        service_dependencies,
    ):
        await InferenceService.generate_article(4)

        service_dependencies.processor.assert_called_once_with(llm_response)

    @pytest.mark.asyncio
    async def test_article_is_saved_with_processed_values(
        self,
        context,
        processed_response,
        service_dependencies,
    ):
        await InferenceService.generate_article(5)

        service_dependencies.create_article.assert_called_once_with(
            capsule=context.capsule,
            title=context.title,
            content=processed_response.content,
            prompt_tokens=processed_response.prompt_tokens,
            completion_tokens=processed_response.completion_tokens,
            total_tokens=processed_response.total_tokens,
            finish_reason=processed_response.finish_reason,
            model=processed_response.model,
        )

    @pytest.mark.asyncio
    async def test_article_generated_event_is_published(
        self,
        saved_article,
        mocker,
        service_dependencies,
    ):
        await InferenceService.generate_article(6)

        from inference.clients.base import STREAM

        service_dependencies.redis.assert_called_once_with(
            STREAM,
            {
                "event": "article.generated",
                "article_id": str(saved_article.id),
            },
        )

    @pytest.mark.asyncio
    async def test_openrouter_exception_is_propagated(
        self,
        context,
        mocker,
    ):
        mocker.patch(
            "inference.clients.base.generate_article_context",
            return_value=context,
        )

        mocker.patch(
            "inference.clients.base.system_prompt",
            return_value="SYSTEM PROMPT",
        )

        mocker.patch(
            "inference.clients.base.PromptBuilder.article",
            return_value="USER PROMPT",
        )

        mocker.patch(
            "inference.clients.base.OpenRouterClient.generate",
            new_callable=AsyncMock,
            side_effect=RuntimeError("OpenRouter unavailable"),
        )

        with pytest.raises(RuntimeError, match="OpenRouter unavailable"):
            await InferenceService.generate_article(1)

    @pytest.mark.asyncio
    async def test_response_processor_exception_is_propagated(
        self,
        context,
        llm_response,
        mocker,
    ):
        mocker.patch(
            "inference.clients.base.generate_article_context",
            return_value=context,
        )

        mocker.patch(
            "inference.clients.base.system_prompt",
            return_value="SYSTEM PROMPT",
        )

        mocker.patch(
            "inference.clients.base.PromptBuilder.article",
            return_value="USER PROMPT",
        )

        mocker.patch(
            "inference.clients.base.OpenRouterClient.generate",
            new_callable=AsyncMock,
            return_value=llm_response,
        )

        mocker.patch(
            "inference.clients.base.ResponseProcessor.article",
            side_effect=ValueError("Malformed response"),
        )

        with pytest.raises(ValueError, match="Malformed response"):
            await InferenceService.generate_article(1)

    @pytest.mark.asyncio
    async def test_article_creation_exception_is_propagated(
        self,
        context,
        llm_response,
        processed_response,
        mocker,
    ):
        mocker.patch(
            "inference.clients.base.generate_article_context",
            return_value=context,
        )

        mocker.patch(
            "inference.clients.base.system_prompt",
            return_value="SYSTEM PROMPT",
        )

        mocker.patch(
            "inference.clients.base.PromptBuilder.article",
            return_value="USER PROMPT",
        )

        mocker.patch(
            "inference.clients.base.OpenRouterClient.generate",
            new_callable=AsyncMock,
            return_value=llm_response,
        )

        mocker.patch(
            "inference.clients.base.ResponseProcessor.article",
            return_value=processed_response,
        )

        create = mocker.patch(
            "inference.clients.base.Articles.objects.create",
            side_effect=RuntimeError("Database failure"),
        )

        redis = mocker.patch("inference.clients.base.redis_client.xadd")

        with pytest.raises(RuntimeError, match="Database failure"):
            await InferenceService.generate_article(1)

        create.assert_called_once()
        redis.assert_not_called()

    @pytest.mark.asyncio
    async def test_redis_exception_is_propagated(
        self,
        service_dependencies,
    ):
        service_dependencies.redis.side_effect = RuntimeError("Redis unavailable")

        with pytest.raises(RuntimeError, match="Redis unavailable"):
            await InferenceService.generate_article(1)

    @pytest.mark.asyncio
    async def test_response_processor_called_before_article_creation(
        self,
        context,
        llm_response,
        processed_response,
        mocker,
    ):
        call_order = []

        mocker.patch(
            "inference.clients.base.generate_article_context",
            return_value=context,
        )

        mocker.patch(
            "inference.clients.base.system_prompt",
            return_value="SYSTEM PROMPT",
        )

        mocker.patch(
            "inference.clients.base.PromptBuilder.article",
            return_value="USER PROMPT",
        )

        async def fake_generate(**kwargs):
            call_order.append("openrouter")
            return llm_response

        def fake_processor(response):
            call_order.append("processor")
            return processed_response

        def fake_create(**kwargs):
            call_order.append("create")
            article = MagicMock()
            article.id = 1
            return article

        def fake_xadd(*args, **kwargs):
            call_order.append("redis")

        mocker.patch(
            "inference.clients.base.OpenRouterClient.generate",
            new=fake_generate,
        )

        mocker.patch(
            "inference.clients.base.ResponseProcessor.article",
            side_effect=fake_processor,
        )

        mocker.patch(
            "inference.clients.base.Articles.objects.create",
            side_effect=fake_create,
        )

        mocker.patch(
            "inference.clients.base.redis_client.xadd",
            side_effect=fake_xadd,
        )

        await InferenceService.generate_article(1)

        assert call_order == [
            "openrouter",
            "processor",
            "create",
            "redis",
        ]

    @pytest.mark.asyncio
    async def test_no_article_created_if_openrouter_fails(
        self,
        context,
        mocker,
    ):
        mocker.patch(
            "inference.clients.base.generate_article_context",
            return_value=context,
        )

        mocker.patch(
            "inference.clients.base.system_prompt",
            return_value="SYSTEM PROMPT",
        )

        mocker.patch(
            "inference.clients.base.PromptBuilder.article",
            return_value="USER PROMPT",
        )

        mocker.patch(
            "inference.clients.base.OpenRouterClient.generate",
            new_callable=AsyncMock,
            side_effect=RuntimeError,
        )

        create = mocker.patch(
            "inference.clients.base.Articles.objects.create",
        )

        redis = mocker.patch(
            "inference.clients.base.redis_client.xadd",
        )

        with pytest.raises(RuntimeError):
            await InferenceService.generate_article(1)

        create.assert_not_called()
        redis.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_redis_event_if_article_creation_fails(
        self,
        context,
        llm_response,
        processed_response,
        mocker,
    ):
        mocker.patch(
            "inference.clients.base.generate_article_context",
            return_value=context,
        )

        mocker.patch(
            "inference.clients.base.system_prompt",
            return_value="SYSTEM PROMPT",
        )

        mocker.patch(
            "inference.clients.base.PromptBuilder.article",
            return_value="USER PROMPT",
        )

        mocker.patch(
            "inference.clients.base.OpenRouterClient.generate",
            new_callable=AsyncMock,
            return_value=llm_response,
        )

        mocker.patch(
            "inference.clients.base.ResponseProcessor.article",
            return_value=processed_response,
        )

        mocker.patch(
            "inference.clients.base.Articles.objects.create",
            side_effect=Exception("Failed to save"),
        )

        redis = mocker.patch(
            "inference.clients.base.redis_client.xadd",
        )

        with pytest.raises(Exception, match="Failed to save"):
            await InferenceService.generate_article(1)

        redis.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_article_returns_saved_article_instance(
        self,
        saved_article,
        service_dependencies,
    ):
        article = await InferenceService.generate_article(1)

        assert article.id == saved_article.id
        assert article is saved_article

    @pytest.mark.asyncio
    async def test_generate_article_only_creates_one_article(
        self,
        service_dependencies,
    ):
        await InferenceService.generate_article(1)

        assert service_dependencies.create_article.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_article_only_publishes_one_event(
        self,
        service_dependencies,
    ):
        await InferenceService.generate_article(1)

        assert service_dependencies.redis.call_count == 1
