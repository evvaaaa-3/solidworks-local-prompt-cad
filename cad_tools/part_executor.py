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
    else:
        raise ValueError(f"Unsupported boss_extrude profile: {profile}")
    exit_sketch(model)
    extrude_boss(model, mm_to_m(float(feature.parameters["depth_mm"])))


def _execute_cut(model: Any, feature: FeatureSpec) -> None:
    profile = feature.parameters.get("profile", "center_circle")
    if profile == "center_circle" or feature.feature_type == "hole":
        select_front_plane(model)
        start_sketch(model)
        _validate_active_cut_sketch(model, feature.feature_id)
        draw_center_circle(model, mm_to_m(float(feature.parameters["diameter_mm"]) / 2.0))
        sketch = _active_sketch(model)
        exit_sketch(model)
        _select_cut_sketch(sketch, feature.feature_id)
    else:
        raise ValueError(f"Unsupported cut_extrude profile: {profile}")
    if feature.parameters.get("through_all", False):
        cut_extrude_through_all(
            model,
            feature_id=feature.feature_id,
            feature_type=feature.feature_type,
            reverse=bool(feature.parameters.get("reverse", False)),
            both_directions=bool(feature.parameters.get("both_directions", True)),
        )
    else:
        depth_mm = float(feature.parameters.get("depth_mm", feature.parameters.get("diameter_mm", 1.0)))
        cut_extrude_depth(model, mm_to_m(depth_mm))


def _active_sketch(model: Any) -> Any:
    sketch_manager = getattr(model, "SketchManager", None)
    if sketch_manager is None:
        return None
    for name in ("ActiveSketch", "GetActiveSketch2"):
        try:
            value = getattr(sketch_manager, name)
            return value() if callable(value) else value
        except Exception:
            continue
    return None


def _validate_active_cut_sketch(model: Any, feature_id: str) -> None:
    if _active_sketch(model) is None:
        raise RuntimeError(f"Cut feature {feature_id} has no active sketch after entering sketch mode.")


def _select_cut_sketch(sketch: Any, feature_id: str) -> None:
    if sketch is None:
        raise RuntimeError(f"Cut feature {feature_id} could not resolve the newly created sketch.")
    for method_name, args in (("Select2", (False, 0)), ("Select", (False,))):
        method = getattr(sketch, method_name, None)
        if method is None:
            continue
        try:
            selected = method(*args)
        except Exception as exc:
            raise RuntimeError(f"Cut feature {feature_id} sketch selection failed: {exc}") from exc
        if selected:
            print(f"[SolidWorks] Cut feature {feature_id}: sketch selected with {method_name}.")
            return
    raise RuntimeError(f"Cut feature {feature_id} sketch selection failed.")
