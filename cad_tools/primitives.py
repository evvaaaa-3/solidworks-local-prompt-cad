"""Deterministic CAD primitive functions with dry-run and SolidWorks modes."""

from __future__ import annotations

from typing import Any

from config import PARTS_DIR, mm_to_m, sanitize_filename
from solidworks_api.connection import connect_solidworks
from solidworks_api.document import create_new_part, save_part
from solidworks_api.features import extrude_boss, revolve_boss
from solidworks_api.sketch import (
    draw_center_circle,
    draw_center_rectangle,
    draw_concentric_circles,
    draw_closed_sphere_revolve_profile,
    draw_cone_revolve_profile,
    draw_torus_revolve_profile,
    exit_sketch,
    select_front_plane,
    start_sketch,
)


def _dimension_label(value_mm: float) -> str:
    return f"{value_mm:g}"


def _dry_result(tool: str, dimensions_mm: dict[str, float], message: str) -> dict[str, Any]:
    print(f"[DRY CAD TOOL] {message}")
    return {
        "status": "dry_run_success",
        "tool": tool,
        "parameters": dimensions_mm,
        "dimensions_mm": dimensions_mm,
        "feature_type": "dry_run",
    }


def _real_result(
    tool: str,
    dimensions_mm: dict[str, float],
    filename: str,
    model: Any,
    feature_type: str,
) -> dict[str, Any]:
    save_result = save_part(model, str(PARTS_DIR / sanitize_filename(filename)))
    return {
        "status": "success",
        "tool": tool,
        "dimensions_mm": dimensions_mm,
        "filepath": save_result["filepath"],
        "feature_type": feature_type,
    }


def _new_model() -> Any:
    sw_app = connect_solidworks(visible=True)
    return create_new_part(sw_app)


def _extrude_rectangle(length_mm: float, width_mm: float, depth_mm: float) -> Any:
    model = _new_model()
    select_front_plane(model)
    start_sketch(model)
    draw_center_rectangle(model, mm_to_m(length_mm), mm_to_m(width_mm))
    exit_sketch(model)
    extrude_boss(model, mm_to_m(depth_mm))
    return model


def _extrude_circle(diameter_mm: float, depth_mm: float) -> Any:
    model = _new_model()
    select_front_plane(model)
    start_sketch(model)
    draw_center_circle(model, mm_to_m(diameter_mm / 2.0))
    exit_sketch(model)
    extrude_boss(model, mm_to_m(depth_mm))
    return model


def _extrude_concentric_circles(
    outer_diameter_mm: float,
    inner_diameter_mm: float,
    depth_mm: float,
) -> Any:
    model = _new_model()
    select_front_plane(model)
    start_sketch(model)
    draw_concentric_circles(
        model,
        mm_to_m(outer_diameter_mm / 2.0),
        mm_to_m(inner_diameter_mm / 2.0),
    )
    exit_sketch(model)
    extrude_boss(model, mm_to_m(depth_mm))
    return model


def _extrude_rectangle_with_center_hole(
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    hole_diameter_mm: float,
) -> Any:
    model = _new_model()
    select_front_plane(model)
    start_sketch(model)
    draw_center_rectangle(model, mm_to_m(length_mm), mm_to_m(width_mm))
    draw_center_circle(model, mm_to_m(hole_diameter_mm / 2.0))
    exit_sketch(model)
    extrude_boss(model, mm_to_m(thickness_mm))
    return model


def _revolve_cone(base_diameter_mm: float, height_mm: float) -> Any:
    model = _new_model()
    select_front_plane(model)
    start_sketch(model)
    draw_cone_revolve_profile(model, mm_to_m(base_diameter_mm / 2.0), mm_to_m(height_mm))
    exit_sketch(model)
    revolve_boss(model, angle_degrees=360.0)
    return model


def _revolve_sphere(diameter_mm: float) -> Any:
    model = _new_model()
    select_front_plane(model)
    start_sketch(model)
    draw_closed_sphere_revolve_profile(model, mm_to_m(diameter_mm / 2.0))
    exit_sketch(model)
    revolve_boss(model, angle_degrees=360.0)
    return model


def _revolve_torus(major_diameter_mm: float, minor_diameter_mm: float) -> Any:
    model = _new_model()
    select_front_plane(model)
    start_sketch(model)
    draw_torus_revolve_profile(
        model,
        mm_to_m(major_diameter_mm / 2.0),
        mm_to_m(minor_diameter_mm / 2.0),
    )
    exit_sketch(model)
    revolve_boss(model, angle_degrees=360.0)
    return model


def create_cube(side_mm: float, dry_run: bool = True) -> dict[str, Any]:
    dimensions = {"side_mm": side_mm}
    if dry_run:
        return _dry_result(
            "create_cube",
            dimensions,
            f"Would create cube with side {side_mm:g} mm.",
        )

    model = _extrude_rectangle(side_mm, side_mm, side_mm)
    filename = f"cube_{_dimension_label(side_mm)}mm.SLDPRT"
    return _real_result("create_cube", dimensions, filename, model, "extrude")


def create_block(
    length_mm: float,
    width_mm: float,
    height_mm: float,
    dry_run: bool = True,
) -> dict[str, Any]:
    dimensions = {
        "length_mm": length_mm,
        "width_mm": width_mm,
        "height_mm": height_mm,
    }
    if dry_run:
        return _dry_result(
            "create_block",
            dimensions,
            f"Would create block {length_mm:g} mm x {width_mm:g} mm x {height_mm:g} mm.",
        )

    model = _extrude_rectangle(length_mm, width_mm, height_mm)
    filename = (
        "block_"
        f"{_dimension_label(length_mm)}x{_dimension_label(width_mm)}x"
        f"{_dimension_label(height_mm)}mm.SLDPRT"
    )
    return _real_result("create_block", dimensions, filename, model, "extrude")


def create_cylinder(
    diameter_mm: float,
    height_mm: float,
    dry_run: bool = True,
) -> dict[str, Any]:
    dimensions = {
        "diameter_mm": diameter_mm,
        "height_mm": height_mm,
    }
    if dry_run:
        return _dry_result(
            "create_cylinder",
            dimensions,
            f"Would create cylinder with diameter {diameter_mm:g} mm and height {height_mm:g} mm.",
        )

    model = _extrude_circle(diameter_mm, height_mm)
    filename = f"cylinder_D{_dimension_label(diameter_mm)}_H{_dimension_label(height_mm)}mm.SLDPRT"
    return _real_result("create_cylinder", dimensions, filename, model, "extrude")


def create_shaft(diameter_mm: float, length_mm: float, dry_run: bool = True) -> dict[str, Any]:
    dimensions = {
        "diameter_mm": diameter_mm,
        "length_mm": length_mm,
    }
    if dry_run:
        return _dry_result(
            "create_shaft",
            dimensions,
            f"Would create shaft with diameter {diameter_mm:g} mm and length {length_mm:g} mm.",
        )

    model = _extrude_circle(diameter_mm, length_mm)
    filename = f"shaft_D{_dimension_label(diameter_mm)}_L{_dimension_label(length_mm)}mm.SLDPRT"
    return _real_result("create_shaft", dimensions, filename, model, "extrude")


def create_disc(diameter_mm: float, thickness_mm: float, dry_run: bool = True) -> dict[str, Any]:
    dimensions = {
        "diameter_mm": diameter_mm,
        "thickness_mm": thickness_mm,
    }
    if dry_run:
        return _dry_result(
            "create_disc",
            dimensions,
            f"Would create disc with diameter {diameter_mm:g} mm and thickness {thickness_mm:g} mm.",
        )

    model = _extrude_circle(diameter_mm, thickness_mm)
    filename = f"disc_D{_dimension_label(diameter_mm)}_T{_dimension_label(thickness_mm)}mm.SLDPRT"
    return _real_result("create_disc", dimensions, filename, model, "extrude")


def create_plate(
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    dry_run: bool = True,
) -> dict[str, Any]:
    dimensions = {
        "length_mm": length_mm,
        "width_mm": width_mm,
        "thickness_mm": thickness_mm,
    }
    if dry_run:
        return _dry_result(
            "create_plate",
            dimensions,
            f"Would create plate {length_mm:g} mm x {width_mm:g} mm x {thickness_mm:g} mm.",
        )

    model = _extrude_rectangle(length_mm, width_mm, thickness_mm)
    filename = (
        "plate_"
        f"{_dimension_label(length_mm)}x{_dimension_label(width_mm)}x"
        f"{_dimension_label(thickness_mm)}mm.SLDPRT"
    )
    return _real_result("create_plate", dimensions, filename, model, "extrude")


def create_tube(
    outer_diameter_mm: float,
    inner_diameter_mm: float,
    height_mm: float,
    dry_run: bool = True,
) -> dict[str, Any]:
    dimensions = {
        "outer_diameter_mm": outer_diameter_mm,
        "inner_diameter_mm": inner_diameter_mm,
        "height_mm": height_mm,
    }
    if dry_run:
        return _dry_result(
            "create_tube",
            dimensions,
            (
                f"Would create tube outer diameter {outer_diameter_mm:g} mm, "
                f"inner diameter {inner_diameter_mm:g} mm, height {height_mm:g} mm."
            ),
        )

    model = _extrude_concentric_circles(outer_diameter_mm, inner_diameter_mm, height_mm)
    filename = (
        f"tube_OD{_dimension_label(outer_diameter_mm)}_ID"
        f"{_dimension_label(inner_diameter_mm)}_H{_dimension_label(height_mm)}mm.SLDPRT"
    )
    return _real_result("create_tube", dimensions, filename, model, "extrude")


def create_plate_with_hole(
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    hole_diameter_mm: float,
    dry_run: bool = True,
) -> dict[str, Any]:
    dimensions = {
        "length_mm": length_mm,
        "width_mm": width_mm,
        "thickness_mm": thickness_mm,
        "hole_diameter_mm": hole_diameter_mm,
    }
    if dry_run:
        return _dry_result(
            "create_plate_with_hole",
            dimensions,
            (
                f"Would create plate {length_mm:g} mm x {width_mm:g} mm x "
                f"{thickness_mm:g} mm with hole diameter {hole_diameter_mm:g} mm."
            ),
        )

    model = _extrude_rectangle_with_center_hole(
        length_mm,
        width_mm,
        thickness_mm,
        hole_diameter_mm,
    )
    filename = (
        "plate_"
        f"{_dimension_label(length_mm)}x{_dimension_label(width_mm)}x"
        f"{_dimension_label(thickness_mm)}_hole_D"
        f"{_dimension_label(hole_diameter_mm)}mm.SLDPRT"
    )
    return _real_result("create_plate_with_hole", dimensions, filename, model, "extrude")


def create_cone(
    base_diameter_mm: float,
    height_mm: float,
    dry_run: bool = True,
) -> dict[str, Any]:
    dimensions = {
        "base_diameter_mm": base_diameter_mm,
        "height_mm": height_mm,
    }
    if dry_run:
        return _dry_result(
            "create_cone",
            dimensions,
            (
                f"Would create cone with base diameter {base_diameter_mm:g} mm "
                f"and height {height_mm:g} mm using a 360 degree revolve."
            ),
        )

    model = _revolve_cone(base_diameter_mm, height_mm)
    filename = f"cone_D{_dimension_label(base_diameter_mm)}_H{_dimension_label(height_mm)}mm.SLDPRT"
    return _real_result("create_cone", dimensions, filename, model, "revolve")


def create_sphere(diameter_mm: float, dry_run: bool = True) -> dict[str, Any]:
    dimensions = {"diameter_mm": diameter_mm}
    if dry_run:
        return _dry_result(
            "create_sphere",
            dimensions,
            f"Would create sphere with diameter {diameter_mm:g} mm using a 360 degree revolve.",
        )

    model = _revolve_sphere(diameter_mm)
    filename = f"sphere_D{_dimension_label(diameter_mm)}mm.SLDPRT"
    return _real_result("create_sphere", dimensions, filename, model, "revolve")


def create_torus(
    major_diameter_mm: float,
    minor_diameter_mm: float,
    dry_run: bool = True,
) -> dict[str, Any]:
    dimensions = {
        "major_diameter_mm": major_diameter_mm,
        "minor_diameter_mm": minor_diameter_mm,
    }
    if dry_run:
        return _dry_result(
            "create_torus",
            dimensions,
            (
                f"Would create torus with major diameter {major_diameter_mm:g} mm "
                f"and minor diameter {minor_diameter_mm:g} mm using a 360 degree revolve."
            ),
        )

    model = _revolve_torus(major_diameter_mm, minor_diameter_mm)
    filename = (
        f"torus_majorD{_dimension_label(major_diameter_mm)}_minorD"
        f"{_dimension_label(minor_diameter_mm)}mm.SLDPRT"
    )
    return _real_result("create_torus", dimensions, filename, model, "revolve")


dry_run_create_cube = create_cube
dry_run_create_block = create_block
dry_run_create_cylinder = create_cylinder
