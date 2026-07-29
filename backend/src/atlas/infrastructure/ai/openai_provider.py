"""OpenAI-compatible explanation provider (Spec 15)."""

import structlog
import httpx

logger = structlog.get_logger(__name__)


class OpenAIExplanationProvider:
    """Call OpenAI chat completions API."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds

    async def generate(self, prompt: str, max_tokens: int) -> str:
        system, user = _split_prompt(prompt)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()


def _split_prompt(prompt: str) -> tuple[str, str]:
    marker = "---\nDecision data:"
    if marker in prompt:
        system, rest = prompt.split(marker, 1)
        return system.strip(), f"Decision data:{rest.strip()}"
    return prompt, "Explain this trading decision."
