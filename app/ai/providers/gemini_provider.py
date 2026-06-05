"""
Google Gemini chat completion provider.
"""

from __future__ import annotations

import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Dict, Optional

from app.ai.providers.base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        genai.configure(api_key=self.api_key)

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
        gemini_model = model or "gemini-1.5-flash"
        fallback_models = [
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro-latest",
            "gemini-2.0-flash",
        ]
        
        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "response_mime_type": "application/json",
        }
        if max_tokens is not None and max_tokens > 0:
            generation_config["max_output_tokens"] = int(max_tokens)

        candidate_models = [gemini_model] + [m for m in fallback_models if m != gemini_model]
        last_error: Exception | None = None
        response = None
        for candidate in candidate_models:
            model_instance = genai.GenerativeModel(
                model_name=candidate,
                system_instruction=system_prompt,
                generation_config=generation_config
            )
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(model_instance.generate_content, user_prompt)
                    response = future.result(timeout=timeout_seconds)
                break
            except FutureTimeoutError as e:
                last_error = RuntimeError(f"Gemini request timed out after {timeout_seconds}s")
                break
            except Exception as e:
                last_error = e
                continue

        if response is None:
            raise RuntimeError(f"Gemini request failed: {last_error}")

        if not response.text:
            raise RuntimeError("Gemini returned empty content")

        return response.text
