"""High-level deterministic assembly workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cad_tools.primitives import create_cylinder, create_disc, create_plate, create_tube
from config import ASSEMBLIES_DIR, mm_to_m, sanitize_filename
from solidworks_api.assembly import (
    create_new_assembly,
    fix_component,
    insert_component,
    save_assembly,
    set_component_position,
)
from solidworks_api.connection import connect_solidworks


def _component(name: str, filepath: str, instance_count: int) -> dict[str, Any]:
    return {
        "name": name,
        "filepath": filepath,
        "filename": Path(filepath).name,
        "instance_count": instance_count,
    }


def _dry_result(assembly_type: str, components: list[dict[str, Any]]) -> dict[str, Any]:
    print(f"[DRY CAD TOOL] Would create assembly: {assembly_type}.")
    return {
        "success": True,
        "status": "dry_run_success",
        "operation": "create_assembly",
        "tool": "create_assembly",
        "assembly_type": assembly_type,
        "filepath": None,
        "filename": None,
        "output_dir": str(ASSEMBLIES_DIR),
        "components": components,
        "message": "Assembly dry-run completed.",
    }


def _save_result(assembly_type: str, assembly_model: Any, components: list[dict[str, Any]]) -> dict[str, Any]:
    filename = sanitize_filename(f"{assembly_type}.SLDASM")
    try:
        save_result = save_assembly(assembly_model, str(ASSEMBLIES_DIR / filename))
    except RuntimeError as exc:
        return {
            "success": False,
            "status": "save_failed",
            "operation": "create_assembly",
            "tool": "create_assembly",
            "assembly_type": assembly_type,
            "filepath": None,
            "filename": None,
            "output_dir": str(ASSEMBLIES_DIR),
            "components": components,
            "message": str(exc),
        }

    filepath = Path(save_result["filepath"])
    return {
        "success": True,
        "status": "success",
        "operation": "create_assembly",
        "tool": "create_assembly",
        "assembly_type": assembly_type,
        "filepath": str(filepath),
        "filename": filepath.name,
        "output_dir": str(filepath.parent),
        "components": components,
        "message": "Assembly created successfully.",
    }


def create_assembly(
    assembly_type: str,
    parameters: dict[str, Any],
    dry_run: bool = True,
) -> dict[str, Any]:
    if assembly_type == "base_plate_with_cylinders":
        return _base_plate_with_cylinders(parameters, dry_run=dry_run)
    if assembly_type == "tube_with_two_end_discs":
        return _tube_with_two_end_discs(parameters, dry_run=dry_run)
    if assembly_type == "simple_shaft_with_two_wheels":
        return _simple_shaft_with_two_wheels(parameters, dry_run=dry_run)
    raise ValueError(f"Unsupported assembly type: {assembly_type}")


def _new_assembly_model() -> Any:
    sw_app = connect_solidworks(visible=True)
    return create_new_assembly(sw_app)


def _insert_instances(assembly_model: Any, part_filepath: str, positions_mm: list[tuple[float, float, float]]) -> None:
    for index, (x_mm, y_mm, z_mm) in enumerate(positions_mm):
        component = insert_component(
            assembly_model,
            part_filepath,
            mm_to_m(x_mm),
            mm_to_m(y_mm),
            mm_to_m(z_mm),
        )
        set_component_position(component, mm_to_m(x_mm), mm_to_m(y_mm), mm_to_m(z_mm))
        if index == 0:
            fix_component(assembly_model, component)


def _base_plate_with_cylinders(parameters: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    assembly_type = "base_plate_with_cylinders"
    components = [
        {"name": "base_plate", "instance_count": 1},
        {"name": "post", "instance_count": int(parameters["post_count"])},
    ]
    if dry_run:
        return _dry_result(assembly_type, components)

    plate = create_plate(
        parameters["base_length_mm"],
        parameters["base_width_mm"],
        parameters["base_thickness_mm"],
        dry_run=False,
    )
    post = create_cylinder(
        parameters["post_diameter_mm"],
        parameters["post_height_mm"],
        dry_run=False,
    )
    component_results = [
        _component("base_plate", plate["filepath"], 1),
        _component("post", post["filepath"], int(parameters["post_count"])),
    ]

    assembly_model = _new_assembly_model()
    _insert_instances(assembly_model, plate["filepath"], [(0.0, 0.0, 0.0)])
    z_mm = (parameters["base_thickness_mm"] + parameters["post_height_mm"]) / 2.0
    _insert_instances(
        assembly_model,
        post["filepath"],
        [(-35.0, 0.0, z_mm), (35.0, 0.0, z_mm)],
    )
    return _save_result(assembly_type, assembly_model, component_results)


def _tube_with_two_end_discs(parameters: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    assembly_type = "tube_with_two_end_discs"
    components = [
        {"name": "tube", "instance_count": 1},
        {"name": "end_disc", "instance_count": int(parameters["cap_count"])},
    ]
    if dry_run:
        return _dry_result(assembly_type, components)

    tube = create_tube(
        parameters["tube_outer_diameter_mm"],
        parameters["tube_inner_diameter_mm"],
        parameters["tube_height_mm"],
        dry_run=False,
    )
    cap = create_disc(
        parameters["cap_diameter_mm"],
        parameters["cap_thickness_mm"],
        dry_run=False,
    )
    component_results = [
        _component("tube", tube["filepath"], 1),
        _component("end_disc", cap["filepath"], int(parameters["cap_count"])),
    ]

    assembly_model = _new_assembly_model()
    _insert_instances(assembly_model, tube["filepath"], [(0.0, 0.0, 0.0)])
    offset = (parameters["tube_height_mm"] + parameters["cap_thickness_mm"]) / 2.0
    _insert_instances(
        assembly_model,
        cap["filepath"],
        [(0.0, 0.0, -offset), (0.0, 0.0, offset)],
    )
    return _save_result(assembly_type, assembly_model, component_results)


def _simple_shaft_with_two_wheels(parameters: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    assembly_type = "simple_shaft_with_two_wheels"
    components = [
        {"name": "shaft", "instance_count": 1},
        {"name": "wheel", "instance_count": int(parameters["wheel_count"])},
    ]
    if dry_run:
        return _dry_result(assembly_type, components)

    shaft = create_cylinder(
        parameters["shaft_diameter_mm"],
        parameters["shaft_length_mm"],
        dry_run=False,
    )
    wheel = create_disc(
        parameters["wheel_diameter_mm"],
        parameters["wheel_thickness_mm"],
        dry_run=False,
    )
    component_results = [
        _component("shaft", shaft["filepath"], 1),
        _component("wheel", wheel["filepath"], int(parameters["wheel_count"])),
    ]

    assembly_model = _new_assembly_model()
    _insert_instances(assembly_model, shaft["filepath"], [(0.0, 0.0, 0.0)])
    offset = (parameters["shaft_length_mm"] - parameters["wheel_thickness_mm"]) / 2.0
    _insert_instances(
        assembly_model,
        wheel["filepath"],
        [(0.0, 0.0, -offset), (0.0, 0.0, offset)],
    )
    return _save_result(assembly_type, assembly_model, component_results)
