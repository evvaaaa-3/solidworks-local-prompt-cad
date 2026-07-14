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
    match = re.search(rf"\b{re.escape(label)}\b\s*(?:of\s*)?({_NUMBER_PATTERN.pattern})", prompt)
    if match is None:
        return None
    return float(match.group(1))


def _step_filename(prompt: str) -> str:
    match = _FILENAME_PATTERN.search(prompt)
    if match is None:
        raise ValueError("Export prompts need a STEP filename, such as 'cube.step'.")
    return match.group(1).strip()


def _parse_assembly_prompt(normalized: str) -> dict[str, Any] | None:
    assembly_words = (
        "assembly",
        "base plate",
        "mounting plate",
        "posts",
        "caps",
        "end discs",
        "end disks",
        "wheels",
        "axle",
    )
    if not any(word in normalized for word in assembly_words):
        return None

    if (
        ("base plate" in normalized or "mounting plate" in normalized or "plate" in normalized)
        and (
            "two cylinders" in normalized
            or "2 cylinders" in normalized
            or "posts" in normalized
            or "cylindrical posts" in normalized
        )
    ):
        return {
            "tool_name": "create_assembly",
            "parameters": {
                "assembly_type": "base_plate_with_cylinders",
            },
        }

    if (
        "tube" in normalized
        or "pipe" in normalized
    ) and (
        "two end discs" in normalized
        or "two end disks" in normalized
        or "end discs" in normalized
        or "end disks" in normalized
        or "two caps" in normalized
        or "end caps" in normalized
        or "circular end plates" in normalized
    ):
        return {
            "tool_name": "create_assembly",
            "parameters": {
                "assembly_type": "tube_with_two_end_discs",
            },
        }

    if (
        ("shaft" in normalized or "axle" in normalized)
        and ("wheels" in normalized or "two wheels" in normalized)
    ):
        return {
            "tool_name": "create_assembly",
            "parameters": {
                "assembly_type": "simple_shaft_with_two_wheels",
            },
        }

    return None


def parse_prompt_rule_based(prompt: str) -> dict[str, Any]:
    """Parse supported CAD prompts into a structured intent dictionary.

    Stage 1 intentionally uses fixed parsing rules only. LLM/Ollama parsing is
    reserved for a later stage.
    """

    normalized = prompt.strip().lower()
    if not normalized:
        raise ValueError("Prompt cannot be empty.")

    assembly_intent = _parse_assembly_prompt(normalized)
    if assembly_intent is not None:
        return assembly_intent

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

    if "torus" in normalized:
        major_diameter = _dimension_after("major diameter", normalized)
        minor_diameter = _dimension_after("minor diameter", normalized)
        tube_diameter = _dimension_after("tube diameter", normalized)

        if minor_diameter is None:
            minor_diameter = tube_diameter

        if major_diameter is None or minor_diameter is None:
            raise ValueError("Torus prompts need major diameter and minor/tube diameter.")

        return {
            "tool_name": "create_torus",
            "parameters": {
                "major_diameter_mm": major_diameter,
                "minor_diameter_mm": minor_diameter,
            },
        }

    if "sphere" in normalized or "ball" in normalized:
        diameter = _dimension_after("diameter", normalized)
        if diameter is None:
            diameter = _first_number(normalized, "sphere diameter")

        return {
            "tool_name": "create_sphere",
            "parameters": {"diameter_mm": diameter},
        }

    if "cone" in normalized:
        base_diameter = _dimension_after("base diameter", normalized)
        diameter = _dimension_after("diameter", normalized)
        height = _dimension_after("height", normalized)

        if base_diameter is None:
            base_diameter = diameter

        if base_diameter is None or height is None:
            values = _numbers(normalized)
            if len(values) < 2:
                raise ValueError("Cone prompts need base diameter and height dimensions.")
            base_diameter, height = values[:2]

        return {
            "tool_name": "create_cone",
            "parameters": {
                "base_diameter_mm": base_diameter,
                "height_mm": height,
            },
        }

    if "tube" in normalized or "hollow cylinder" in normalized:
        outer_diameter = _dimension_after("outer diameter", normalized)
        inner_diameter = _dimension_after("inner diameter", normalized)
        height = _dimension_after("height", normalized)

        if outer_diameter is None or inner_diameter is None or height is None:
            raise ValueError(
                "Tube prompts need outer diameter, inner diameter, and height dimensions."
            )

        return {
            "tool_name": "create_tube",
            "parameters": {
                "outer_diameter_mm": outer_diameter,
                "inner_diameter_mm": inner_diameter,
                "height_mm": height,
            },
        }

    if "plate" in normalized and "hole" in normalized:
        length = _dimension_after("length", normalized)
        width = _dimension_after("width", normalized)
        thickness = _dimension_after("thickness", normalized)
        hole_diameter = _dimension_after("hole diameter", normalized)

        values = _numbers(normalized)
        if length is None or width is None or thickness is None:
            if len(values) < 3:
                raise ValueError(
                    "Plate with hole prompts need length, width, thickness, and hole diameter."
                )
            length, width, thickness = values[:3]

        if hole_diameter is None:
            if len(values) < 4:
                raise ValueError("Plate with hole prompts need a hole diameter.")
            hole_diameter = values[-1]

        return {
            "tool_name": "create_plate_with_hole",
            "parameters": {
                "length_mm": length,
                "width_mm": width,
                "thickness_mm": thickness,
                "hole_diameter_mm": hole_diameter,
            },
        }

    if "disc" in normalized or "disk" in normalized:
        diameter = _dimension_after("diameter", normalized)
        thickness = _dimension_after("thickness", normalized)

        if diameter is None or thickness is None:
            values = _numbers(normalized)
            if len(values) < 2:
                raise ValueError("Disc prompts need diameter and thickness dimensions.")
            diameter, thickness = values[:2]

        return {
            "tool_name": "create_disc",
            "parameters": {
                "diameter_mm": diameter,
                "thickness_mm": thickness,
            },
        }

    if "plate" in normalized:
        length = _dimension_after("length", normalized)
        width = _dimension_after("width", normalized)
        thickness = _dimension_after("thickness", normalized)

        if length is None or width is None or thickness is None:
            values = _numbers(normalized)
            if len(values) < 3:
                raise ValueError("Plate prompts need length, width, and thickness dimensions.")
            length, width, thickness = values[:3]

        return {
            "tool_name": "create_plate",
            "parameters": {
                "length_mm": length,
                "width_mm": width,
                "thickness_mm": thickness,
            },
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
