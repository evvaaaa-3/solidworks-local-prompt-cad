"""Translate generic component specs into reusable SolidWorks part files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from cad_tools import primitives
from cad_tools.assembly_planner import AssemblyPlan, ComponentSpec


@dataclass(frozen=True)
class ComponentBuildResult:
    component_id: str
    name: str
    type: str
    role: str
    filepath: str
    filename: str
    instance_count: int
    reused: bool


def create_component_part(component: ComponentSpec, dry_run: bool = False) -> ComponentBuildResult:
    creator = _creator_for(component)
    result = creator(component, dry_run)
    filepath = result.get("filepath") or f"<pending:{component.id}>"
    return ComponentBuildResult(
        component_id=component.id,
        name=component.id,
        type=component.type,
        role=component.role,
        filepath=filepath,
        filename=Path(filepath).name if not filepath.startswith("<pending:") else "",
        instance_count=component.quantity,
        reused=component.reuse_part,
    )


def create_components_for_plan(plan: AssemblyPlan, dry_run: bool = False) -> dict[str, ComponentBuildResult]:
    created: dict[tuple[str, tuple[tuple[str, float], ...]], ComponentBuildResult] = {}
    results: dict[str, ComponentBuildResult] = {}
    for component in plan.components:
        key = (component.type, tuple(sorted(component.dimensions.items())))
        if component.reuse_part and key in created:
            existing = created[key]
            results[component.id] = ComponentBuildResult(
                component_id=component.id,
                name=component.id,
                type=component.type,
                role=component.role,
                filepath=existing.filepath,
                filename=existing.filename,
                instance_count=component.quantity,
                reused=True,
            )
            continue
        built = create_component_part(component, dry_run=dry_run)
        created[key] = built
        results[component.id] = built
    return results


def _creator_for(component: ComponentSpec) -> Callable[[ComponentSpec, bool], dict[str, object]]:
    creators: dict[str, Callable[[ComponentSpec, bool], dict[str, object]]] = {
        "plate": _create_plate,
        "plate_with_hole": _create_plate_with_hole,
        "cylinder": _create_cylinder,
        "pin": _create_cylinder,
        "shaft": _create_shaft,
        "tube": _create_tube,
        "disc": _create_disc,
        "wheel": _create_disc,
    }
    try:
        return creators[component.type]
    except KeyError as exc:
        raise ValueError(f"Unsupported component type: {component.type}") from exc


def _create_plate(component: ComponentSpec, dry_run: bool) -> dict[str, object]:
    dimensions = component.dimensions
    return primitives.create_plate(
        dimensions["length_mm"],
        dimensions["width_mm"],
        dimensions["thickness_mm"],
        dry_run=dry_run,
    )


def _create_plate_with_hole(component: ComponentSpec, dry_run: bool) -> dict[str, object]:
    dimensions = component.dimensions
    return primitives.create_plate_with_hole(
        dimensions["length_mm"],
        dimensions["width_mm"],
        dimensions["thickness_mm"],
        dimensions["hole_diameter_mm"],
        dry_run=dry_run,
    )


def _create_cylinder(component: ComponentSpec, dry_run: bool) -> dict[str, object]:
    dimensions = component.dimensions
    return primitives.create_cylinder(
        dimensions["diameter_mm"],
        dimensions["height_mm"],
        dry_run=dry_run,
    )


def _create_shaft(component: ComponentSpec, dry_run: bool) -> dict[str, object]:
    dimensions = component.dimensions
    return primitives.create_cylinder(
        dimensions["diameter_mm"],
        dimensions["length_mm"],
        dry_run=dry_run,
    )


def _create_tube(component: ComponentSpec, dry_run: bool) -> dict[str, object]:
    dimensions = component.dimensions
    return primitives.create_tube(
        dimensions["outer_diameter_mm"],
        dimensions["inner_diameter_mm"],
        dimensions["height_mm"],
        dry_run=dry_run,
    )


def _create_disc(component: ComponentSpec, dry_run: bool) -> dict[str, object]:
    dimensions = component.dimensions
    return primitives.create_disc(
        dimensions["diameter_mm"],
        dimensions["thickness_mm"],
        dry_run=dry_run,
    )
