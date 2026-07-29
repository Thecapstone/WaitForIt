import os

from dotenv import load_dotenv
import httpx

load_dotenv()


class OpenRouterClient:
    """
    Thin wrapper around the OpenRouter Chat Completions API.
    """

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")

        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured.")

    async def generate(
        self,
        *,
        system_prompt: str,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        """
        Sends a request to OpenRouter and returns the raw JSON response.
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
            )

            response.raise_for_status()

            return response.json()
