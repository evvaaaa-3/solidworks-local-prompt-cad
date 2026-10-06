"""Face-relative placement math for generic assembly planning."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from cad_tools.cad_schemas import TransformSpec
from cad_tools.transforms import solidworks_transform_array

Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class FaceFrame:
    """Assembly-space coordinate frame for a planar mounting face."""

    origin: Vector3
    normal: Vector3
    u_axis: Vector3
    v_axis: Vector3


@dataclass(frozen=True)
class FacePlacementSpec:
    """Declarative placement of a component relative to a target face frame."""

    target_instance_id: str
    target_reference: str
    u_offset_mm: float
    v_offset_mm: float
    normal_offset_mm: float = 0.0
    source_axis: str = "-Z"
    target_axis: str = "face_normal"
    component_axis_length_mm: float = 0.0


def normalize(vector: Vector3) -> Vector3:
    length = math.sqrt(sum(value * value for value in vector))
    if length <= 1e-12:
        raise ValueError("Cannot normalize a zero-length vector.")
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def dot(a: Vector3, b: Vector3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vector3, b: Vector3) -> Vector3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def scale(vector: Vector3, factor: float) -> Vector3:
    return (vector[0] * factor, vector[1] * factor, vector[2] * factor)


def local_uv_to_world(frame: FaceFrame, u_mm: float, v_mm: float, normal_offset_mm: float = 0.0) -> Vector3:
    """Convert face-local UVN coordinates into assembly-space millimetres."""

    return add(
        add(frame.origin, scale(frame.u_axis, u_mm)),
        add(scale(frame.v_axis, v_mm), scale(frame.normal, normal_offset_mm)),
    )


def frame_from_normal(origin: Vector3, normal: Vector3, preferred_u: Vector3 = (1.0, 0.0, 0.0)) -> FaceFrame:
    """Create a stable orthonormal frame from a face origin and normal."""

    n_axis = normalize(normal)
    u_candidate = preferred_u
    if abs(dot(normalize(u_candidate), n_axis)) > 0.95:
        u_candidate = (0.0, 1.0, 0.0)
    u_axis = normalize(cross(u_candidate, n_axis))
    v_axis = normalize(cross(n_axis, u_axis))
    return FaceFrame(origin=origin, normal=n_axis, u_axis=u_axis, v_axis=v_axis)


def rotation_matrix_from_transform(transform: TransformSpec) -> tuple[Vector3, Vector3, Vector3]:
    data = solidworks_transform_array(transform)
    return (
        (data[0], data[1], data[2]),
        (data[3], data[4], data[5]),
        (data[6], data[7], data[8]),
    )


def apply_rotation(matrix: tuple[Vector3, Vector3, Vector3], vector: Vector3) -> Vector3:
    return (
        dot(matrix[0], vector),
        dot(matrix[1], vector),
        dot(matrix[2], vector),
    )


def top_face_frame_from_box(transform: TransformSpec) -> FaceFrame:
    """Return the top mounting face frame for parts extruded from the sketch plane.

    Current primitive parts sketch on the Front Plane and extrude away from that
    sketch plane, so the insertion origin is the mounting face center.
    """

    matrix = rotation_matrix_from_transform(transform)
    origin = (transform.translation_x, transform.translation_y, transform.translation_z)
    normal = normalize(apply_rotation(matrix, (0.0, 0.0, 1.0)))
    u_axis = normalize(apply_rotation(matrix, (1.0, 0.0, 0.0)))
    v_axis = normalize(cross(normal, u_axis))
    return FaceFrame(origin=origin, normal=normal, u_axis=u_axis, v_axis=v_axis)


def axis_vector(axis: str) -> Vector3:
    normalized_axis = axis.strip().upper()
    sign = -1.0 if normalized_axis.startswith("-") else 1.0
    key = normalized_axis[-1]
    if key == "X":
        return (sign, 0.0, 0.0)
    if key == "Y":
        return (0.0, sign, 0.0)
    if key == "Z":
        return (0.0, 0.0, sign)
    raise ValueError("axis must be X, Y, or Z, optionally prefixed by '-'.")


def rotation_align_vectors(source: Vector3, target: Vector3) -> tuple[Vector3, Vector3, Vector3]:
    """Return a rotation matrix that aligns source vector to target vector."""

    s = normalize(source)
    t = normalize(target)
    v = cross(s, t)
    c = max(-1.0, min(1.0, dot(s, t)))
    if c > 1.0 - 1e-9:
        return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    if c < -1.0 + 1e-9:
        helper = (1.0, 0.0, 0.0) if abs(s[0]) < 0.9 else (0.0, 1.0, 0.0)
        axis = normalize(cross(s, helper))
        return _axis_angle_matrix(axis, math.pi)
    skew = (
        (0.0, -v[2], v[1]),
        (v[2], 0.0, -v[0]),
        (-v[1], v[0], 0.0),
    )
    factor = 1.0 / (1.0 + c)
    skew2 = _matrix_multiply(skew, skew)
    return tuple(
        tuple((1.0 if row == col else 0.0) + skew[row][col] + skew2[row][col] * factor for col in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def face_relative_component_origin(frame: FaceFrame, placement: FacePlacementSpec) -> Vector3:
    """Compute component insertion origin from face-local placement."""

    base_point = local_uv_to_world(
        frame,
        placement.u_offset_mm,
        placement.v_offset_mm,
        placement.normal_offset_mm,
    )
    source = axis_vector(placement.source_axis)
    source_to_base_sign = -1.0 if dot(source, (0.0, 0.0, 1.0)) < 0 else 1.0
    origin_offset = placement.component_axis_length_mm if placement.source_axis.strip().startswith("-") else 0.0
    return add(base_point, scale(frame.normal, origin_offset * source_to_base_sign * -1.0))


def _axis_angle_matrix(axis: Vector3, angle: float) -> tuple[Vector3, Vector3, Vector3]:
    x, y, z = axis
    c = math.cos(angle)
    s = math.sin(angle)
    one = 1.0 - c
    return (
        (c + x * x * one, x * y * one - z * s, x * z * one + y * s),
        (y * x * one + z * s, c + y * y * one, y * z * one - x * s),
        (z * x * one - y * s, z * y * one + x * s, c + z * z * one),
    )


def _matrix_multiply(a: Iterable[Vector3], b: Iterable[Vector3]) -> tuple[Vector3, Vector3, Vector3]:
    a_rows = tuple(a)
    b_rows = tuple(b)
    columns = tuple(zip(*b_rows))
    return tuple(tuple(dot(row, col) for col in columns) for row in a_rows)  # type: ignore[return-value]
