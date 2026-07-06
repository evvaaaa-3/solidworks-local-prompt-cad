"""SolidWorks sketch helpers."""

from __future__ import annotations

from typing import Any


def _call_if_available(obj: Any, name: str, *args: Any) -> Any:
    member = getattr(obj, name, None)
    if member is None:
        return None
    if callable(member):
        return member(*args)
    return member


def _select_by_id(model: Any, plane_name: str) -> bool:
    try:
        selected = model.Extension.SelectByID2(
            plane_name, "PLANE", 0, 0, 0, False, 0, None, 0
        )
    except Exception as exc:
        print(f"[SolidWorks] SelectByID2 failed for {plane_name}: {exc}")
        return False

    print(f"[SolidWorks] SelectByID2 {plane_name}: {bool(selected)}")
    return bool(selected)


def _select_feature_by_name(model: Any, plane_name: str) -> bool:
    try:
        feature = model.FeatureByName(plane_name)
    except Exception as exc:
        print(f"[SolidWorks] FeatureByName failed for {plane_name}: {exc}")
        return False

    if feature is None:
        print(f"[SolidWorks] FeatureByName {plane_name}: not found")
        return False

    try:
        selected = feature.Select2(False, 0)
    except Exception as exc:
        print(f"[SolidWorks] Feature.Select2 failed for {plane_name}: {exc}")
        return False

    print(f"[SolidWorks] FeatureByName Select2 {plane_name}: {bool(selected)}")
    return bool(selected)


def select_front_plane(model: Any) -> bool:
    try:
        _call_if_available(model, "ClearSelection2", True)
    except Exception as exc:
        print(f"[SolidWorks] ClearSelection2 failed; continuing: {exc}")

    for plane_name in ("Front Plane", "Front", "Plane1"):
        if _select_by_id(model, plane_name):
            return True

    for plane_name in ("Front Plane", "Front", "Plane1"):
        if _select_feature_by_name(model, plane_name):
            return True

    raise RuntimeError(
        "Could not select Front Plane. Active document exists, but plane selection failed."
    )


def start_sketch(model: Any) -> None:
    try:
        print("[SolidWorks] Entering sketch mode.")
        model.SketchManager.InsertSketch(True)
        print("[SolidWorks] Sketch mode entered.")
    except Exception as exc:
        raise RuntimeError("Could not enter SolidWorks sketch mode.") from exc


def exit_sketch(model: Any) -> None:
    try:
        model.SketchManager.InsertSketch(True)
    except Exception as exc:
        raise RuntimeError("Could not exit SolidWorks sketch mode.") from exc


def draw_center_rectangle(model: Any, length_m: float, width_m: float) -> Any:
    half_length = length_m / 2.0
    half_width = width_m / 2.0

    try:
        rectangle = model.SketchManager.CreateCornerRectangle(
            -half_length,
            -half_width,
            0,
            half_length,
            half_width,
            0,
        )
    except Exception as exc:
        raise RuntimeError("Could not draw centered rectangle in SolidWorks.") from exc

    if rectangle is None:
        raise RuntimeError("SolidWorks failed to create centered rectangle.")
    return rectangle


def draw_center_circle(model: Any, radius_m: float) -> Any:
    try:
        circle = model.SketchManager.CreateCircleByRadius(0, 0, 0, radius_m)
    except Exception as exc:
        raise RuntimeError("Could not draw centered circle in SolidWorks.") from exc

    if circle is None:
        raise RuntimeError("SolidWorks failed to create centered circle.")
    return circle


def draw_concentric_circles(model: Any, outer_radius_m: float, inner_radius_m: float) -> Any:
    outer_circle = draw_center_circle(model, outer_radius_m)
    inner_circle = draw_center_circle(model, inner_radius_m)
    return {
        "outer_circle": outer_circle,
        "inner_circle": inner_circle,
    }


def _create_line(model: Any, start_x_m: float, start_y_m: float, end_x_m: float, end_y_m: float) -> Any:
    try:
        line = model.SketchManager.CreateLine(start_x_m, start_y_m, 0, end_x_m, end_y_m, 0)
    except Exception as exc:
        raise RuntimeError("Could not draw sketch line in SolidWorks.") from exc

    if line is None:
        raise RuntimeError("SolidWorks failed to create sketch line.")
    return line


def draw_centerline_axis(
    model: Any,
    start_x_m: float,
    start_y_m: float,
    end_x_m: float,
    end_y_m: float,
) -> Any:
    print("[SolidWorks] Drawing revolve centerline axis.")
    try:
        centerline = model.SketchManager.CreateCenterLine(
            start_x_m, start_y_m, 0, end_x_m, end_y_m, 0
        )
    except Exception as exc:
        raise RuntimeError("Could not draw SolidWorks revolve centerline axis.") from exc

    if centerline is None:
        raise RuntimeError("SolidWorks failed to create revolve centerline axis.")
    print("[SolidWorks] Revolve centerline axis created.")
    return centerline


def draw_cone_revolve_profile(model: Any, base_radius_m: float, height_m: float) -> dict[str, Any]:
    print("[SolidWorks] Drawing cone revolve profile.")
    bottom_y = -height_m / 2.0
    top_y = height_m / 2.0
    axis = draw_centerline_axis(model, 0, bottom_y, 0, top_y)
    base_edge = _create_line(model, 0, bottom_y, base_radius_m, bottom_y)
    slope_edge = _create_line(model, base_radius_m, bottom_y, 0, top_y)
    axis_edge = _create_line(model, 0, top_y, 0, bottom_y)
    print("[SolidWorks] Cone revolve profile created.")
    return {
        "axis": axis,
        "base_edge": base_edge,
        "slope_edge": slope_edge,
        "axis_edge": axis_edge,
    }


def draw_sphere_revolve_profile(model: Any, radius_m: float) -> dict[str, Any]:
    print("[SolidWorks] Drawing sphere revolve profile.")
    axis = draw_centerline_axis(model, 0, -radius_m, 0, radius_m)
    try:
        arc = model.SketchManager.CreateArc(
            0,
            0,
            0,
            0,
            radius_m,
            0,
            0,
            -radius_m,
            0,
            1,
        )
    except Exception as exc:
        raise RuntimeError("Could not draw SolidWorks sphere semicircle arc.") from exc

    if arc is None:
        raise RuntimeError("SolidWorks failed to create sphere semicircle arc.")
    diameter_edge = _create_line(model, 0, radius_m, 0, -radius_m)
    print("[SolidWorks] Sphere revolve profile created.")
    return {
        "axis": axis,
        "arc": arc,
        "diameter_edge": diameter_edge,
    }


def draw_closed_sphere_revolve_profile(model: Any, radius_m: float) -> dict[str, Any]:
    print("[SolidWorks] Drawing closed sphere revolve profile.")
    axis_span = radius_m * 1.2
    axis = draw_centerline_axis(model, 0, -axis_span, 0, axis_span)

    try:
        arc = model.SketchManager.CreateArc(
            0,
            0,
            0,
            0,
            radius_m,
            0,
            0,
            -radius_m,
            0,
            1,
        )
    except Exception as exc:
        raise RuntimeError("Could not draw closed sphere semicircle arc.") from exc

    if arc is None:
        raise RuntimeError("SolidWorks failed to create closed sphere semicircle arc.")

    diameter_edge = _create_line(model, 0, radius_m, 0, -radius_m)
    entities = {
        "axis": axis,
        "arc": arc,
        "diameter_edge": diameter_edge,
    }
    print(
        "[SolidWorks] Closed sphere profile entities: "
        f"axis={axis is not None}, arc={arc is not None}, "
        f"diameter_edge={diameter_edge is not None}"
    )
    print("[SolidWorks] Closed sphere revolve profile created.")
    return entities


def draw_torus_revolve_profile(
    model: Any,
    major_radius_m: float,
    minor_radius_m: float,
) -> dict[str, Any]:
    print("[SolidWorks] Drawing torus revolve profile.")
    axis_span = major_radius_m + minor_radius_m
    axis = draw_centerline_axis(model, 0, -axis_span, 0, axis_span)
    try:
        circle = model.SketchManager.CreateCircleByRadius(
            major_radius_m, 0, 0, minor_radius_m
        )
    except Exception as exc:
        raise RuntimeError("Could not draw SolidWorks torus circle profile.") from exc

    if circle is None:
        raise RuntimeError("SolidWorks failed to create torus circle profile.")
    print("[SolidWorks] Torus revolve profile created.")
    return {
        "axis": axis,
        "circle": circle,
    }
