class BaseLLMClient:
    """Base client for llm"""

    def generate(self, prompt: str, system_prompt: str | None = None) -> str: ...
