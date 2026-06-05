"""
OpenAI chat completion provider.
"""

from __future__ import annotations

import httpx
from typing import Any, Dict, Optional

from app.ai.providers.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: int = 30,
        model: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        openai_model = model or "gpt-4o-mini"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": openai_model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if max_tokens is not None and max_tokens > 0:
            payload["max_tokens"] = int(max_tokens)

        # Force JSON output where supported
        if response_format:
            payload["response_format"] = response_format
        else:
            payload["response_format"] = {"type": "json_object"}

        url = "https://api.openai.com/v1/chat/completions"

        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=payload)

        if resp.status_code >= 400:
            raise RuntimeError(f"OpenAI request failed: {resp.status_code} {resp.text}")

        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Unexpected OpenAI response shape: {e}") from e

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenAI returned empty content")

        return content

