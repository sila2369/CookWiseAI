"""
LLM provider abstraction layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseLLMProvider(ABC):
    @abstractmethod
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
        """
        Generate model output text.

        Must return the raw assistant content (string).
        """

