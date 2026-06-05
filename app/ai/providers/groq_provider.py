"""
Groq Cloud chat completion provider (OpenAI-compatible).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.ai.providers.base import BaseLLMProvider


class GroqProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.groq.com/openai/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

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
        groq_model = model or "llama-3.3-70b-versatile"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": groq_model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": response_format or {"type": "json_object"},
        }
        if max_tokens is not None and max_tokens > 0:
            payload["max_tokens"] = int(max_tokens)

        url = f"{self.base_url}/chat/completions"
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=payload)

        if resp.status_code >= 400:
            raise RuntimeError(f"Groq request failed: {resp.status_code} {resp.text}")

        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError(f"Unexpected Groq response shape: {exc}") from exc

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Groq returned empty content")

        return content

