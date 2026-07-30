"""Feature-based part execution layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cad_tools.cad_schemas import FeatureSpec, PartPlan
from config import PARTS_DIR, mm_to_m, sanitize_filename
from solidworks_api.connection import connect_solidworks
from solidworks_api.document import create_new_part, save_part
from solidworks_api.features import (
    chamfer,
    cut_extrude_depth,
    cut_extrude_through_all,
    extrude_boss,
    fillet,
    shell,
)
from solidworks_api.sketch import (
    draw_center_circle,
    draw_center_rectangle,
    draw_concentric_circles,
    exit_sketch,
    select_front_plane,
    start_sketch,
)


def execute_part_plan(plan: PartPlan, dry_run: bool = True) -> dict[str, Any]:
    """Execute a declarative PartPlan through ordered feature operations."""

    ordered = [feature for feature in plan.ordered_features() if feature.enabled]
    if dry_run:
        return {
            "status": "dry_run_success",
            "tool": "create_part_plan",
            "part_name": plan.part_name,
            "filepath": f"<pending:{plan.output_filename}>",
            "features_executed": [feature.feature_id for feature in ordered],
            "feature_types": [feature.feature_type for feature in ordered],
        }

    sw_app = connect_solidworks(visible=True)
    model = create_new_part(sw_app)
    executed: list[str] = []
    for feature in ordered:
        _execute_feature(model, feature)
        executed.append(feature.feature_id)

    target = PARTS_DIR / sanitize_filename(plan.output_filename)
    save_result = save_part(model, str(target))
    return {
        "status": "success",
        "tool": "create_part_plan",
        "part_name": plan.part_name,
        "filepath": save_result["filepath"],
        "filename": Path(save_result["filepath"]).name,
        "features_executed": executed,
        "feature_types": [feature.feature_type for feature in ordered],
    }


def _execute_feature(model: Any, feature: FeatureSpec) -> None:
    if feature.feature_type == "boss_extrude":
        _execute_boss_extrude(model, feature)
        return
    if feature.feature_type in {"cut_extrude", "hole"}:
        _execute_cut(model, feature)
        return
    if feature.feature_type == "fillet":
        fillet(model, mm_to_m(float(feature.parameters["radius_mm"])))
        return
    if feature.feature_type == "chamfer":
        chamfer(model, mm_to_m(float(feature.parameters["distance_mm"])))
        return
    if feature.feature_type == "shell":
        shell(model, mm_to_m(float(feature.parameters["thickness_mm"])))
        return
    raise ValueError(f"Unsupported feature type: {feature.feature_type}")


def _execute_boss_extrude(model: Any, feature: FeatureSpec) -> None:
    profile = feature.parameters.get("profile")
    select_front_plane(model)
    start_sketch(model)
    if profile == "center_rectangle":
        draw_center_rectangle(
            model,
            mm_to_m(float(feature.parameters["length_mm"])),
            mm_to_m(float(feature.parameters["width_mm"])),
        )
    elif profile == "center_rectangle_with_center_hole":
        draw_center_rectangle(
            model,
            mm_to_m(float(feature.parameters["length_mm"])),
            mm_to_m(float(feature.parameters["width_mm"])),
        )
        draw_center_circle(model, mm_to_m(float(feature.parameters["hole_diameter_mm"]) / 2.0))
    elif profile == "center_circle":
        draw_center_circle(model, mm_to_m(float(feature.parameters["diameter_mm"]) / 2.0))
    elif profile == "concentric_circles":
        draw_concentric_circles(
            model,
            mm_to_m(float(feature.parameters["outer_diameter_mm"]) / 2.0),
            mm_to_m(float(feature.parameters["inner_diameter_mm"]) / 2.0),
        )
    else:
        raise ValueError(f"Unsupported boss_extrude profile: {profile}")
    exit_sketch(model)
    extrude_boss(model, mm_to_m(float(feature.parameters["depth_mm"])))


def _execute_cut(model: Any, feature: FeatureSpec) -> None:
    if feature.feature_type == "hole":
        select_front_plane(model)
        start_sketch(model)
        draw_center_circle(model, mm_to_m(float(feature.parameters["diameter_mm"]) / 2.0))
        exit_sketch(model)
    if feature.parameters.get("through_all", False):
        cut_extrude_through_all(model)
    else:
        depth_mm = float(feature.parameters.get("depth_mm", feature.parameters.get("diameter_mm", 1.0)))
        cut_extrude_depth(model, mm_to_m(depth_mm))
