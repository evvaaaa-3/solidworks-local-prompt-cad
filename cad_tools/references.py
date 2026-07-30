"""Reference validation helpers for generic part features and assembly mates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cad_tools.cad_schemas import ReferenceSpec


_NAMED_REFERENCES: dict[str, ReferenceSpec] = {
    "origin": ReferenceSpec(entity_type="component_origin", reference_name="Origin"),
    "front_plane": ReferenceSpec(entity_type="front_plane", reference_name="Front Plane"),
    "top_plane": ReferenceSpec(entity_type="top_plane", reference_name="Top Plane"),
    "right_plane": ReferenceSpec(entity_type="right_plane", reference_name="Right Plane"),
    "axis": ReferenceSpec(entity_type="axis", selection_rule="primary_axis"),
    "center": ReferenceSpec(entity_type="center", selection_rule="component_center"),
    "top_face": ReferenceSpec(entity_type="planar_face", selection_rule="maximum_z"),
    "bottom_face": ReferenceSpec(entity_type="planar_face", selection_rule="minimum_z"),
    "start_face": ReferenceSpec(entity_type="planar_face", selection_rule="minimum_z"),
    "end_face": ReferenceSpec(entity_type="planar_face", selection_rule="maximum_z"),
    "end_a": ReferenceSpec(entity_type="planar_face", selection_rule="minimum_z"),
    "end_b": ReferenceSpec(entity_type="planar_face", selection_rule="maximum_z"),
    "inner_face": ReferenceSpec(entity_type="planar_face", selection_rule="inner"),
    "outer_edge": ReferenceSpec(entity_type="outer_edge", selection_rule="largest_loop"),
    "cylindrical_face": ReferenceSpec(entity_type="cylindrical_face", selection_rule="largest_radius"),
}


@dataclass(frozen=True)
class ResolvedReference:
    """Reference resolved against an inserted component for COM selection."""

    component_id: str
    selector: ReferenceSpec
    sw_entity: Any


def coerce_reference(value: str | ReferenceSpec | None) -> ReferenceSpec | None:
    """Convert legacy string references into structured selectors."""

    if value is None or value == "":
        return None
    if isinstance(value, ReferenceSpec):
        return value
    normalized = value.strip().lower().replace(" ", "_")
    if normalized in _NAMED_REFERENCES:
        return _NAMED_REFERENCES[normalized]
    raise ValueError(f"Unknown reference selector: {value}")


def validate_reference_selector(selector: ReferenceSpec, known_feature_ids: set[str] | None = None) -> None:
    """Validate a selector without touching SolidWorks COM."""

    if selector.feature_id and known_feature_ids is not None and selector.feature_id not in known_feature_ids:
        raise ValueError(f"Reference selector points to unknown feature_id: {selector.feature_id}")
    if selector.entity_type in {"feature_face", "feature_edge"} and not selector.feature_id:
        raise ValueError(f"{selector.entity_type} selectors require feature_id")
    if selector.entity_type == "face_normal_direction" and selector.direction is None:
        raise ValueError("face_normal_direction selectors require direction")


def resolve_component_reference(
    component_id: str,
    selector: ReferenceSpec,
    component: Any,
    resolver: Any,
) -> ResolvedReference:
    """Resolve a structured selector using a COM-specific resolver object."""

    validate_reference_selector(selector)
    try:
        sw_entity = resolver.resolve(component, selector)
    except Exception as exc:
        raise ValueError(f"Could not resolve {selector.entity_type} on {component_id}: {exc}") from exc
    if sw_entity is None:
        raise ValueError(f"Could not resolve {selector.entity_type} on {component_id}")
    return ResolvedReference(component_id=component_id, selector=selector, sw_entity=sw_entity)
