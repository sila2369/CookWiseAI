"""
Ollama chat completion provider.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.ai.providers.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str) -> None:
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
        ollama_model = model or "llama3.1:8b"
        prompt = f"{system_prompt}\n\n{user_prompt}"
        payload: Dict[str, Any] = {
            "model": ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
            },
        }
        if max_tokens is not None and max_tokens > 0:
            payload["options"]["num_predict"] = int(max_tokens)
        if response_format and response_format.get("type") != "json_object":
            payload.pop("format", None)

        url = f"{self.base_url}/api/generate"
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(url, json=payload)

        if resp.status_code >= 400:
            raise RuntimeError(f"Ollama request failed: {resp.status_code} {resp.text}")

        data = resp.json()
        content = data.get("response")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ollama returned empty content")
        return content

