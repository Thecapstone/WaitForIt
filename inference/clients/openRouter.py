# inference/clients/openrouter.py

import os

from dotenv import load_dotenv
import httpx

load_dotenv()


class OpenRouterClient:
    """
    Thin asynchronous client for the OpenRouter Chat Completions API.
    """

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self) -> None:
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
        Generate a completion from OpenRouter.

        Parameters
        ----------
        system_prompt:
            The system instruction given to the model.

        prompt:
            The user prompt.

        model:
            OpenRouter model identifier.

        temperature:
            Sampling temperature.

        max_tokens:
            Maximum number of completion tokens.

        Returns
        -------
        dict
            Raw JSON response returned by OpenRouter.

        Raises
        ------
        RuntimeError
            If the API response is malformed.

        httpx.HTTPStatusError
            If the request returns a non-2xx response.

        httpx.RequestError
            For connection and timeout errors.
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv(
                "OPENROUTER_SITE_URL",
                "http://localhost:8000",
            ),
            "X-Title": os.getenv(
                "OPENROUTER_APP_NAME",
                "WaitForIt",
            ),
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

            data = response.json()

        if "choices" not in data:
            raise RuntimeError("OpenRouter response did not contain 'choices'.")

        if not data["choices"]:
            raise RuntimeError("OpenRouter returned an empty choices list.")

        return data
