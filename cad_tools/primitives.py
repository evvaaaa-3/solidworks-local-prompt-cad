"""Deterministic CAD primitive functions with Stage 1 dry-run support."""

from __future__ import annotations

from typing import Any

from config import PARTS_DIR, mm_to_m, sanitize_filename
from solidworks_api.connection import connect_solidworks
from solidworks_api.document import create_new_part, save_part
from solidworks_api.features import extrude_boss
from solidworks_api.sketch import (
    draw_center_circle,
    draw_center_rectangle,
    exit_sketch,
    select_front_plane,
    start_sketch,
)


def _dimension_label(value_mm: float) -> str:
    return f"{value_mm:g}"


def create_cube(side_mm: float, dry_run: bool = True) -> dict[str, Any]:
    if not dry_run:
        side_m = mm_to_m(side_mm)
        sw_app = connect_solidworks(visible=True)
        model = create_new_part(sw_app)
        select_front_plane(model)
        start_sketch(model)
        draw_center_rectangle(model, side_m, side_m)
        exit_sketch(model)
        extrude_boss(model, side_m)

        filename = sanitize_filename(f"cube_{_dimension_label(side_mm)}mm.SLDPRT")
        save_result = save_part(model, str(PARTS_DIR / filename))
        return {
            "status": "success",
            "tool": "create_cube",
            "parameters": {"side_mm": side_mm},
            "filepath": save_result["filepath"],
        }

    result = {
        "status": "dry_run_success",
        "tool": "create_cube",
        "parameters": {"side_mm": side_mm},
    }
    print(f"[DRY CAD TOOL] Would create cube with side {side_mm:g} mm.")
    return result


def create_block(
    length_mm: float,
    width_mm: float,
    height_mm: float,
    dry_run: bool = True,
) -> dict[str, Any]:
    if not dry_run:
        length_m = mm_to_m(length_mm)
        width_m = mm_to_m(width_mm)
        height_m = mm_to_m(height_mm)
        sw_app = connect_solidworks(visible=True)
        model = create_new_part(sw_app)
        select_front_plane(model)
        start_sketch(model)
        draw_center_rectangle(model, length_m, width_m)
        exit_sketch(model)
        extrude_boss(model, height_m)

        filename = sanitize_filename(
            "block_"
            f"{_dimension_label(length_mm)}x{_dimension_label(width_mm)}x"
            f"{_dimension_label(height_mm)}mm.SLDPRT"
        )
        save_result = save_part(model, str(PARTS_DIR / filename))
        return {
            "status": "success",
            "tool": "create_block",
            "parameters": {
                "length_mm": length_mm,
                "width_mm": width_mm,
                "height_mm": height_mm,
            },
            "filepath": save_result["filepath"],
        }

    result = {
        "status": "dry_run_success",
        "tool": "create_block",
        "parameters": {
            "length_mm": length_mm,
            "width_mm": width_mm,
            "height_mm": height_mm,
        },
    }
    print(
        f"[DRY CAD TOOL] Would create block {length_mm:g} mm x "
        f"{width_mm:g} mm x {height_mm:g} mm."
    )
    return result


def create_cylinder(
    diameter_mm: float,
    height_mm: float,
    dry_run: bool = True,
) -> dict[str, Any]:
    if not dry_run:
        radius_m = mm_to_m(diameter_mm / 2.0)
        height_m = mm_to_m(height_mm)
        sw_app = connect_solidworks(visible=True)
        model = create_new_part(sw_app)
        select_front_plane(model)
        start_sketch(model)
        draw_center_circle(model, radius_m)
        exit_sketch(model)
        extrude_boss(model, height_m)

        filename = sanitize_filename(
            f"cylinder_D{_dimension_label(diameter_mm)}_H{_dimension_label(height_mm)}mm.SLDPRT"
        )
        save_result = save_part(model, str(PARTS_DIR / filename))
        return {
            "status": "success",
            "tool": "create_cylinder",
            "parameters": {
                "diameter_mm": diameter_mm,
                "height_mm": height_mm,
            },
            "filepath": save_result["filepath"],
        }

    result = {
        "status": "dry_run_success",
        "tool": "create_cylinder",
        "parameters": {
            "diameter_mm": diameter_mm,
            "height_mm": height_mm,
        },
    }
    print(
        f"[DRY CAD TOOL] Would create cylinder with diameter {diameter_mm:g} mm "
        f"and height {height_mm:g} mm."
    )
    return result


dry_run_create_cube = create_cube
dry_run_create_block = create_block
dry_run_create_cylinder = create_cylinder
