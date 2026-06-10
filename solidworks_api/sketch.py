"""SolidWorks sketch helpers."""

from __future__ import annotations

from typing import Any


def select_front_plane(model: Any) -> bool:
    try:
        selected = model.Extension.SelectByID2(
            "Front Plane", "PLANE", 0, 0, 0, False, 0, None, 0
        )
    except Exception as exc:
        raise RuntimeError("Could not select Front Plane in SolidWorks.") from exc

    if not selected:
        raise RuntimeError("SolidWorks failed to select Front Plane.")
    return True


def start_sketch(model: Any) -> None:
    try:
        model.SketchManager.InsertSketch(True)
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
