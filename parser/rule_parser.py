"""Deterministic rule-based prompt parser for Stage 1."""

from __future__ import annotations

import re
from typing import Any


_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
_FILENAME_PATTERN = re.compile(r"\b([A-Za-z0-9_.-]+\.(?:step|stp))\b", re.IGNORECASE)


def _numbers(prompt: str) -> list[float]:
    return [float(value) for value in _NUMBER_PATTERN.findall(prompt)]


def _first_number(prompt: str, field_name: str) -> float:
    values = _numbers(prompt)
    if not values:
        raise ValueError(f"Missing {field_name} dimension.")
    return values[0]


def _dimension_after(label: str, prompt: str) -> float | None:
    match = re.search(rf"\b{label}\b\s*(?:of\s*)?({_NUMBER_PATTERN.pattern})", prompt)
    if match is None:
        return None
    return float(match.group(1))


def _step_filename(prompt: str) -> str:
    match = _FILENAME_PATTERN.search(prompt)
    if match is None:
        raise ValueError("Export prompts need a STEP filename, such as 'cube.step'.")
    return match.group(1).strip()


def parse_prompt_rule_based(prompt: str) -> dict[str, Any]:
    """Parse supported CAD prompts into a structured intent dictionary.

    Stage 1 intentionally uses fixed parsing rules only. LLM/Ollama parsing is
    reserved for a later stage.
    """

    normalized = prompt.strip().lower()
    if not normalized:
        raise ValueError("Prompt cannot be empty.")

    if "export" in normalized and "step" in normalized:
        return {
            "tool_name": "export_step",
            "parameters": {"filename": _step_filename(normalized)},
        }

    if "export" in normalized or "save" in normalized:
        filename = _step_filename(normalized)
        return {
            "tool_name": "export_step",
            "parameters": {"filename": filename},
        }

    if "cube" in normalized:
        return {
            "tool_name": "create_cube",
            "parameters": {"side_mm": _first_number(normalized, "cube side")},
        }

    if "block" in normalized or "box" in normalized or "rectangular prism" in normalized:
        length = _dimension_after("length", normalized)
        width = _dimension_after("width", normalized)
        height = _dimension_after("height", normalized)

        if length is None or width is None or height is None:
            values = _numbers(normalized)
            if len(values) < 3:
                raise ValueError("Block prompts need length, width, and height dimensions.")
            length, width, height = values[:3]

        return {
            "tool_name": "create_block",
            "parameters": {
                "length_mm": length,
                "width_mm": width,
                "height_mm": height,
            },
        }

    if "cylinder" in normalized:
        diameter = _dimension_after("diameter", normalized)
        height = _dimension_after("height", normalized)

        if diameter is None or height is None:
            values = _numbers(normalized)
            if len(values) < 2:
                raise ValueError("Cylinder prompts need diameter and height dimensions.")
            diameter, height = values[:2]

        return {
            "tool_name": "create_cylinder",
            "parameters": {
                "diameter_mm": diameter,
                "height_mm": height,
            },
        }

    raise ValueError("Unsupported CAD prompt.")


def parse_prompt(prompt: str) -> dict[str, Any]:
    return parse_prompt_rule_based(prompt)
