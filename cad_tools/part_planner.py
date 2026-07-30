"""Generic feature-based part plan generation for reusable components."""

from __future__ import annotations

from typing import Any

from cad_tools.cad_schemas import FeatureSpec, PartPlan, ReferenceSpec
from config import sanitize_filename


def build_part_plan(
    *,
    part_name: str,
    component_type: str,
    dimensions: dict[str, float],
    features: tuple[Any, ...] = (),
    material: str | None = None,
) -> PartPlan:
    """Build a generic feature sequence for a component spec."""

    base_feature = _base_feature_for(component_type, dimensions)
    converted_features = [
        _coerce_feature(feature, index + 10)
        for index, feature in enumerate(features)
    ]
    filename = sanitize_filename(f"{part_name}_{component_type}.SLDPRT")
    return PartPlan(
        part_name=part_name,
        base_feature=base_feature,
        features=converted_features,
        material=material,
        output_filename=filename,
    )


def _base_feature_for(component_type: str, dimensions: dict[str, float]) -> FeatureSpec:
    if component_type == "plate":
        return FeatureSpec(
            feature_id="base_plate",
            feature_type="boss_extrude",
            parameters={
                "profile": "center_rectangle",
                "length_mm": dimensions["length_mm"],
                "width_mm": dimensions["width_mm"],
                "depth_mm": dimensions["thickness_mm"],
            },
            reference_geometry=[ReferenceSpec(entity_type="front_plane", reference_name="Front Plane")],
            operation_order=0,
        )
    if component_type == "plate_with_hole":
        return FeatureSpec(
            feature_id="base_plate",
            feature_type="boss_extrude",
            parameters={
                "profile": "center_rectangle_with_center_hole",
                "length_mm": dimensions["length_mm"],
                "width_mm": dimensions["width_mm"],
                "depth_mm": dimensions["thickness_mm"],
                "hole_diameter_mm": dimensions["hole_diameter_mm"],
            },
            reference_geometry=[ReferenceSpec(entity_type="front_plane", reference_name="Front Plane")],
            operation_order=0,
        )
    if component_type in {"cylinder", "pin"}:
        return _circular_extrude("base_cylinder", dimensions["diameter_mm"], dimensions["height_mm"])
    if component_type == "shaft":
        return _circular_extrude("shaft_body", dimensions["diameter_mm"], dimensions["length_mm"])
    if component_type in {"disc", "wheel"}:
        return _circular_extrude("disc_body", dimensions["diameter_mm"], dimensions["thickness_mm"])
    if component_type == "tube":
        return FeatureSpec(
            feature_id="tube_body",
            feature_type="boss_extrude",
            parameters={
                "profile": "concentric_circles",
                "outer_diameter_mm": dimensions["outer_diameter_mm"],
                "inner_diameter_mm": dimensions["inner_diameter_mm"],
                "depth_mm": dimensions["height_mm"],
            },
            reference_geometry=[ReferenceSpec(entity_type="front_plane", reference_name="Front Plane")],
            operation_order=0,
        )
    raise ValueError(f"Unsupported component type: {component_type}")


def _circular_extrude(feature_id: str, diameter_mm: float, depth_mm: float) -> FeatureSpec:
    return FeatureSpec(
        feature_id=feature_id,
        feature_type="boss_extrude",
        parameters={
            "profile": "center_circle",
            "diameter_mm": diameter_mm,
            "depth_mm": depth_mm,
        },
        reference_geometry=[ReferenceSpec(entity_type="front_plane", reference_name="Front Plane")],
        operation_order=0,
    )


def _coerce_feature(feature: Any, default_order: int) -> FeatureSpec:
    if isinstance(feature, FeatureSpec):
        return feature
    feature_type = getattr(feature, "type", None) or getattr(feature, "feature_type", None)
    dimensions = dict(getattr(feature, "dimensions", {}) or getattr(feature, "parameters", {}) or {})
    feature_id = getattr(feature, "name", "") or getattr(feature, "feature_id", "") or f"{feature_type}_{default_order}"
    if feature_type in {"through_hole", "hole"}:
        return FeatureSpec(
            feature_id=feature_id,
            feature_type="hole",
            parameters={"diameter_mm": dimensions["diameter_mm"], "through_all": True},
            reference_geometry=[ReferenceSpec(entity_type="planar_face", selection_rule="maximum_z")],
            operation_order=default_order,
        )
    return FeatureSpec(
        feature_id=feature_id,
        feature_type=feature_type,
        parameters=dimensions,
        operation_order=default_order,
    )
