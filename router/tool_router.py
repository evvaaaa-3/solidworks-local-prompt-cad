"""Route validated intents to deterministic CAD tool functions."""

from __future__ import annotations

from typing import Any

from cad_tools.exports import export_step
from cad_tools.primitives import create_block, create_cube, create_cylinder


def route_intent(validated_intent: Any, dry_run: bool = True) -> dict[str, Any]:
    tool_name = validated_intent.tool_name
    parameters = validated_intent.parameters.model_dump()

    if dry_run:
        print(f"[DRY RUN] Routing to {tool_name}")
        print(f"[DRY RUN] Parameters: {parameters}")

    return _call_tool(tool_name, parameters)


def _call_tool(tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "create_cube":
        return create_cube(side_mm=parameters["side_mm"])

    if tool_name == "create_block":
        return create_block(
            length_mm=parameters["length_mm"],
            width_mm=parameters["width_mm"],
            height_mm=parameters["height_mm"],
        )

    if tool_name == "create_cylinder":
        return create_cylinder(
            diameter_mm=parameters["diameter_mm"],
            height_mm=parameters["height_mm"],
        )

    if tool_name == "export_step":
        return export_step(filename=parameters["filename"])

    raise ValueError(f"Unsupported tool: {tool_name}")
