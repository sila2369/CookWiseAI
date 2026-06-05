"""
JSON utilities.
"""

from __future__ import annotations

import json
import re
import logging
from typing import Any, Dict, Optional, Sequence


logger = logging.getLogger(__name__)


def safe_json_parse(
    text: str,
    *,
    fallback: Optional[Dict[str, Any]] = None,
    extract_first_object: bool = True,
    required_keys: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
    Safely parse JSON from model/provider output.

    Rules:
    - Try direct json.loads first.
    - If fails and extract_first_object=True:
      - extract the first JSON value substring (object or array)
      - retry parsing extracted substring
    - If still fails:
      - return fallback structure (default: {"raw": text, "error": "..."}).
    """
    fallback_obj: Dict[str, Any] = fallback or {"raw": text}

    if not isinstance(text, str):
        return {**fallback_obj, "error": "Input is not a string"}

    def _validate_required_keys(obj: Any) -> Optional[str]:
        if not required_keys:
            return None
        if not isinstance(obj, dict):
            return "Type validation failed: expected an object for required_keys"
        missing = [k for k in required_keys if k not in obj]
        if missing:
            return f"Missing required keys: {missing}"
        return None

    def _normalize_parsed(parsed: Any) -> Dict[str, Any]:
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"data": parsed}
        return {"value": parsed}

    def _extract_first_json_value(s: str) -> Optional[str]:
        # Accept fenced blocks first.
        # Example: ```json\n{...}\n```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s.strip(), flags=re.IGNORECASE)
        if fence_match:
            candidate = fence_match.group(1)
            if candidate and ("{" in candidate or "[" in candidate):
                return candidate.strip()

        # Find first '{' or '[' and then extract the balanced JSON value.
        start_idx = None
        start_ch = None
        for i, ch in enumerate(s):
            if ch in ("{", "["):
                start_idx = i
                start_ch = ch
                break
        if start_idx is None or start_ch is None:
            return None

        stack: list[str] = []
        in_str = False
        quote_char = '"'
        escaped = False

        i = start_idx
        while i < len(s):
            ch = s[i]

            if in_str:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote_char:
                    in_str = False
                i += 1
                continue

            if ch in ('"', "'"):
                in_str = True
                quote_char = ch
                i += 1
                continue

            if ch in ("{", "["):
                stack.append(ch)
            elif ch in ("}", "]"):
                if not stack:
                    return None
                open_ch = stack.pop()
                if open_ch == "{":
                    if ch != "}":
                        return None
                else:
                    if ch != "]":
                        return None

                if not stack:
                    return s[start_idx : i + 1]

            i += 1

        return None

    # 1) Direct parse attempt (supports nested JSON already)
    try:
        parsed = json.loads(text)
        validation_error = _validate_required_keys(parsed)
        if validation_error:
            return {**fallback_obj, "error": validation_error}
        return _normalize_parsed(parsed)
    except Exception as first_exc:
        logger.warning(
            "safe_json_parse: direct json.loads failed (%s): %s",
            type(first_exc).__name__,
            str(first_exc)[:300],
        )

    # If caller doesn't want extraction, stop here.
    if not extract_first_object:
        return {**fallback_obj, "error": "json.loads failed (no extraction attempted)"}

    # 2) Extract first JSON value attempt (object OR array)
    candidate = _extract_first_json_value(text)
    if not candidate:
        return {**fallback_obj, "error": "No JSON value found (object/array)"}

    try:
        parsed2 = json.loads(candidate)
        validation_error = _validate_required_keys(parsed2)
        if validation_error:
            return {**fallback_obj, "error": validation_error, "extracted": candidate[:2000]}
        return _normalize_parsed(parsed2)
    except Exception as second_exc:
        logger.warning(
            "safe_json_parse: extracted json.loads failed (%s): %s",
            type(second_exc).__name__,
            str(second_exc)[:300],
        )
        return {
            **fallback_obj,
            "error": f"Safe JSON parse failed: {type(second_exc).__name__}",
            "extracted": candidate[:2000],
        }

