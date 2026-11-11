"""Conservative normalization of known LLM parameter aliases."""

from __future__ import annotations

from typing import Any

from schemas.intent_schema import TOOL_PARAMETER_MODELS


def canonicalize_intent(intent: dict[str, Any]) -> dict[str, Any]:
    """Map unitless field aliases only when the selected tool makes them unambiguous."""
    tool_name = intent.get("tool_name")
    parameter_model = TOOL_PARAMETER_MODELS.get(tool_name)
    parameters = intent.get("parameters")
    if parameter_model is None or not isinstance(parameters, dict):
        return intent

    expected_fields = set(parameter_model.model_fields)
    normalized_parameters: dict[str, Any] = {}
    for key, value in parameters.items():
        canonical_key = _canonical_parameter_name(key, expected_fields)
        if canonical_key in normalized_parameters and canonical_key != key:
            continue
        normalized_parameters[canonical_key] = value

    return {**intent, "parameters": normalized_parameters}


def _canonical_parameter_name(key: str, expected_fields: set[str]) -> str:
    if key in expected_fields:
        return key

    millimeter_key = f"{key}_mm"
    if millimeter_key in expected_fields:
        return millimeter_key

    if key in {"length", "length_mm"} and "height_mm" in expected_fields and "length_mm" not in expected_fields:
        return "height_mm"
    if key in {"height", "height_mm"} and "length_mm" in expected_fields and "height_mm" not in expected_fields:
        return "length_mm"
    return key
