"""
Grok (xAI) chat completion provider.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.ai.providers.base import BaseLLMProvider


class GrokProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.x.ai/v1") -> None:
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
        grok_model = model or "grok-2-latest"
        fallback_models = [
            "grok-3-mini",
            "grok-3-latest",
            "grok-beta",
        ]
        candidate_models = [grok_model] + [m for m in fallback_models if m != grok_model]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"
        last_error: str = "unknown"
        with httpx.Client(timeout=timeout_seconds) as client:
            for candidate in candidate_models:
                payload: Dict[str, Any] = {
                    "model": candidate,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                }
                if max_tokens is not None and max_tokens > 0:
                    payload["max_tokens"] = int(max_tokens)
                if response_format:
                    payload["response_format"] = response_format
                else:
                    payload["response_format"] = {"type": "json_object"}

                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code >= 400:
                    body = resp.text
                    last_error = f"{resp.status_code} {body}"
                    if resp.status_code == 400 and "Model not found" in body:
                        continue
                    raise RuntimeError(f"Grok request failed: {last_error}")

                data = resp.json()
                try:
                    content = data["choices"][0]["message"]["content"]
                except Exception as exc:
                    raise RuntimeError(f"Unexpected Grok response shape: {exc}") from exc

                if not isinstance(content, str) or not content.strip():
                    raise RuntimeError("Grok returned empty content")

                return content

        raise RuntimeError(f"Grok request failed: {last_error}")

