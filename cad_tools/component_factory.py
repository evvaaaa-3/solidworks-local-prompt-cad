"""Translate generic component specs into reusable SolidWorks part files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cad_tools.assembly_planner import AssemblyPlan, ComponentSpec
from cad_tools.part_executor import execute_part_plan
from cad_tools.part_planner import build_part_plan


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
    part_plan: dict[str, Any] | None = None
    features_executed: tuple[str, ...] = ()


def create_component_part(component: ComponentSpec, dry_run: bool = False) -> ComponentBuildResult:
    """Create or dry-run a reusable component part from a generic PartPlan."""

    part_plan = build_part_plan(
        part_name=component.id,
        component_type=component.type,
        dimensions=component.dimensions,
        features=component.features,
        material=getattr(component, "material", None),
    )
    result = execute_part_plan(part_plan, dry_run=dry_run)
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
        part_plan=part_plan.model_dump(),
        features_executed=tuple(result.get("features_executed", ())),
    )


def create_components_for_plan(plan: AssemblyPlan, dry_run: bool = False) -> dict[str, ComponentBuildResult]:
    created: dict[tuple[str, tuple[tuple[str, float], ...]], ComponentBuildResult] = {}
    results: dict[str, ComponentBuildResult] = {}
    for component in plan.components:
        feature_key = tuple(
            sorted(
                (
                    getattr(feature, "name", "") or getattr(feature, "feature_id", ""),
                    getattr(feature, "type", "") or getattr(feature, "feature_type", ""),
                    tuple(sorted((getattr(feature, "dimensions", {}) or {}).items())),
                )
                for feature in component.features
            )
        )
        key = (component.type, tuple(sorted(component.dimensions.items())), feature_key)
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
                part_plan=existing.part_plan,
                features_executed=existing.features_executed,
            )
            continue
        built = create_component_part(component, dry_run=dry_run)
        created[key] = built
        results[component.id] = built
    return results
