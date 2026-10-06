"""Transform helpers for assembly placement.

Planner transforms use millimetres for translation and degrees for rotations.
SolidWorks COM receives metres for translation and radians encoded into the
component transform rotation matrix.
"""

from __future__ import annotations

import math
from typing import Iterable

from cad_tools.cad_schemas import TransformSpec
from config import mm_to_m


def translation_transform(x_mm: float, y_mm: float, z_mm: float) -> TransformSpec:
    """Create a translation-only transform in planner units."""

    return TransformSpec(translation_x=x_mm, translation_y=y_mm, translation_z=z_mm)


def axis_rotation_transform(axis: str, degrees: float) -> TransformSpec:
    """Create an axis-aligned rotation transform in degrees."""

    if axis == "x":
        return TransformSpec(rotation_x=degrees)
    if axis == "y":
        return TransformSpec(rotation_y=degrees)
    if axis == "z":
        return TransformSpec(rotation_z=degrees)
    raise ValueError("axis must be 'x', 'y', or 'z'")


def combined_transform(
    translation_mm: Iterable[float] = (0.0, 0.0, 0.0),
    rotation_deg: Iterable[float] = (0.0, 0.0, 0.0),
) -> TransformSpec:
    """Create a combined translation and XYZ Euler rotation transform."""

    tx, ty, tz = tuple(translation_mm)
    rx, ry, rz = tuple(rotation_deg)
    return TransformSpec(
        translation_x=tx,
        translation_y=ty,
        translation_z=tz,
        rotation_x=rx,
        rotation_y=ry,
        rotation_z=rz,
    )


def transform_translation_m(transform: TransformSpec) -> tuple[float, float, float]:
    """Return SolidWorks translation values in metres."""

    return (
        mm_to_m(transform.translation_x),
        mm_to_m(transform.translation_y),
        mm_to_m(transform.translation_z),
    )


def transform_rotation_rad(transform: TransformSpec) -> tuple[float, float, float]:
    """Return XYZ Euler rotation values in radians."""

    return (
        math.radians(transform.rotation_x),
        math.radians(transform.rotation_y),
        math.radians(transform.rotation_z),
    )


def has_rotation(transform: TransformSpec) -> bool:
    """Return whether a transform includes any axis rotation."""

    return any(
        abs(value) > 1e-9
        for value in (transform.rotation_x, transform.rotation_y, transform.rotation_z)
    )


def m_to_mm(value_m: float) -> float:
    """Convert SolidWorks metre values back to planner millimetres."""

    return value_m * 1000.0


def transform_array_translation_mm(array_data: Iterable[float]) -> tuple[float, float, float] | None:
    """Read SolidWorks transform translation entries as millimetres."""

    values = list(array_data)
    if len(values) < 12:
        return None
    return (m_to_mm(values[9]), m_to_mm(values[10]), m_to_mm(values[11]))


def align_axis_to_axis(source_axis: str, target_axis: str) -> TransformSpec:
    """Return a simple axis-aligned rotation that maps one primary axis to another."""

    source = source_axis.strip().lower()
    target = target_axis.strip().lower()
    if source == target:
        return TransformSpec()
    rotations = {
        ("x", "y"): TransformSpec(rotation_z=90.0),
        ("x", "z"): TransformSpec(rotation_y=-90.0),
        ("y", "x"): TransformSpec(rotation_z=-90.0),
        ("y", "z"): TransformSpec(rotation_x=90.0),
        ("z", "x"): TransformSpec(rotation_y=90.0),
        ("z", "y"): TransformSpec(rotation_x=-90.0),
    }
    try:
        return rotations[(source, target)]
    except KeyError as exc:
        raise ValueError("source_axis and target_axis must be x, y, or z") from exc


def solidworks_transform_array(transform: TransformSpec) -> list[float]:
    """Build a SolidWorks-compatible 4x4 rigid transform array.

    The array uses row-major rotation terms followed by translation at indices
    9, 10, and 11 to match the existing SolidWorks wrapper behaviour.
    """

    rx, ry, rz = transform_rotation_rad(transform)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)

    # Rz * Ry * Rx, a conventional intrinsic XYZ Euler composition.
    r00 = cz * cy
    r01 = cz * sy * sx - sz * cx
    r02 = cz * sy * cx + sz * sx
    r10 = sz * cy
    r11 = sz * sy * sx + cz * cx
    r12 = sz * sy * cx - cz * sx
    r20 = -sy
    r21 = cy * sx
    r22 = cy * cx
    tx, ty, tz = transform_translation_m(transform)
    return [r00, r01, r02, r10, r11, r12, r20, r21, r22, tx, ty, tz, 1.0, 0.0, 0.0, 0.0]
