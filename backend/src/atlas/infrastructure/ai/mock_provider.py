"""Mock LLM provider for CI and local dev (Spec 15)."""

import json
import re

from atlas.domain.services.explanation_prompt import mock_explanation_from_payload


class MockExplanationProvider:
    """Deterministic explanations without external API calls."""

    name = "mock"

    async def generate(self, prompt: str, max_tokens: int) -> str:
        payload = _extract_payload(prompt)
        text = mock_explanation_from_payload(payload)
        if max_tokens > 0 and len(text.split()) > max_tokens:
            return " ".join(text.split()[:max_tokens])
        return text


def _extract_payload(prompt: str) -> dict:
    match = re.search(r"Decision data:\s*(\{.*\})\s*\Z", prompt, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
