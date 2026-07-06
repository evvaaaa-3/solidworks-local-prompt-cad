"""Route validated intents to deterministic CAD tool functions."""

from __future__ import annotations

from typing import Any

from cad_tools.exports import export_step
from cad_tools.primitives import (
    create_block,
    create_cone,
    create_cube,
    create_cylinder,
    create_disc,
    create_plate,
    create_plate_with_hole,
    create_sphere,
    create_torus,
    create_tube,
)


def route_intent(validated_intent: Any, dry_run: bool = True) -> dict[str, Any]:
    tool_name = validated_intent.tool_name
    parameters = validated_intent.parameters.model_dump()

    if dry_run:
        print(f"[DRY RUN] Routing to {tool_name}")
        print(f"[DRY RUN] Parameters: {parameters}")

    return _call_tool(tool_name, parameters, dry_run=dry_run)


def _call_tool(tool_name: str, parameters: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    if tool_name == "create_cube":
        return create_cube(side_mm=parameters["side_mm"], dry_run=dry_run)

    if tool_name == "create_block":
        return create_block(
            length_mm=parameters["length_mm"],
            width_mm=parameters["width_mm"],
            height_mm=parameters["height_mm"],
            dry_run=dry_run,
        )

    if tool_name == "create_cylinder":
        return create_cylinder(
            diameter_mm=parameters["diameter_mm"],
            height_mm=parameters["height_mm"],
            dry_run=dry_run,
        )

    if tool_name == "create_disc":
        return create_disc(
            diameter_mm=parameters["diameter_mm"],
            thickness_mm=parameters["thickness_mm"],
            dry_run=dry_run,
        )

    if tool_name == "create_plate":
        return create_plate(
            length_mm=parameters["length_mm"],
            width_mm=parameters["width_mm"],
            thickness_mm=parameters["thickness_mm"],
            dry_run=dry_run,
        )

    if tool_name == "create_tube":
        return create_tube(
            outer_diameter_mm=parameters["outer_diameter_mm"],
            inner_diameter_mm=parameters["inner_diameter_mm"],
            height_mm=parameters["height_mm"],
            dry_run=dry_run,
        )

    if tool_name == "create_plate_with_hole":
        return create_plate_with_hole(
            length_mm=parameters["length_mm"],
            width_mm=parameters["width_mm"],
            thickness_mm=parameters["thickness_mm"],
            hole_diameter_mm=parameters["hole_diameter_mm"],
            dry_run=dry_run,
        )

    if tool_name == "create_cone":
        return create_cone(
            base_diameter_mm=parameters["base_diameter_mm"],
            height_mm=parameters["height_mm"],
            dry_run=dry_run,
        )

    if tool_name == "create_sphere":
        return create_sphere(
            diameter_mm=parameters["diameter_mm"],
            dry_run=dry_run,
        )

    if tool_name == "create_torus":
        return create_torus(
            major_diameter_mm=parameters["major_diameter_mm"],
            minor_diameter_mm=parameters["minor_diameter_mm"],
            dry_run=dry_run,
        )

    if tool_name == "export_step":
        return export_step(filename=parameters["filename"], dry_run=dry_run)

    raise ValueError(f"Unsupported tool: {tool_name}")
