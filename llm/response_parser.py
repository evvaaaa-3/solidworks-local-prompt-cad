"""Robust JSON extraction for model responses."""

from __future__ import annotations

import json
import re
from typing import Any


_FENCED_JSON = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def extract_json_object(text: str) -> dict[str, Any]:
    candidates = []
    fenced = _FENCED_JSON.findall(text)
    candidates.extend(fenced)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])
    candidates.append(text)

    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("invalid_json")
