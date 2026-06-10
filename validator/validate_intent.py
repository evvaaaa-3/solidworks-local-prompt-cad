"""Validation entry point for parsed CAD intents."""

from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter, ValidationError

from schemas.intent_schema import Intent


_intent_adapter = TypeAdapter(Intent)


def validate_intent(intent_dict: dict[str, Any]) -> Intent:
    try:
        return _intent_adapter.validate_python(intent_dict)
    except ValidationError as exc:
        raise ValueError(f"Invalid CAD intent: {exc}") from exc
