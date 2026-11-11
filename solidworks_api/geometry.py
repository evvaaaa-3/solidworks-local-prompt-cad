"""SolidWorks component geometry helpers for assembly placement."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable

from cad_tools.face_placement import Vector3, cross, dot, local_uv_to_world, normalize
from cad_tools.transforms import m_to_mm
from config import mm_to_m


@dataclass(frozen=True)
class PlanarFaceFrame:
    face: Any
    point_mm: Vector3
    normal: Vector3
    u_axis: Vector3
    v_axis: Vector3

    @property
    def origin(self) -> Vector3:
        return self.point_mm


@dataclass(frozen=True)
class CylindricalAxis:
    face: Any
    point_mm: Vector3
    axis: Vector3


@dataclass(frozen=True)
class ComponentMountFrame:
    bottom_face: PlanarFaceFrame
    native_axis: Vector3
    source_u: Vector3
    source_v: Vector3


def component_transform_array(component: Any) -> list[float]:
    transform = component.Transform2
    data = getattr(transform, "ArrayData")
    if callable(data):
        data = data()
    values = list(data)
    if len(values) < 12:
        raise RuntimeError("Component Transform2.ArrayData did not contain a rigid transform.")
    return values


def set_component_transform_array(component: Any, data: Iterable[float]) -> None:
    transform = component.Transform2
    current = list(getattr(transform, "ArrayData")() if callable(getattr(transform, "ArrayData")) else transform.ArrayData)
    values = list(data)
    if len(current) >= len(values):
        current[: len(values)] = values
        transform.ArrayData = current
    else:
        transform.ArrayData = values
    component.Transform2 = transform


def transform_point_mm(data: list[float], point_mm: Vector3) -> Vector3:
    point_m = tuple(mm_to_m(value) for value in point_mm)
    x = data[0] * point_m[0] + data[1] * point_m[1] + data[2] * point_m[2] + data[9]
    y = data[3] * point_m[0] + data[4] * point_m[1] + data[5] * point_m[2] + data[10]
    z = data[6] * point_m[0] + data[7] * point_m[1] + data[8] * point_m[2] + data[11]
    return (m_to_mm(x), m_to_mm(y), m_to_mm(z))


def transform_vector(data: list[float], vector: Vector3) -> Vector3:
    return normalize(
        (
            data[0] * vector[0] + data[1] * vector[1] + data[2] * vector[2],
            data[3] * vector[0] + data[4] * vector[1] + data[5] * vector[2],
            data[6] * vector[0] + data[7] * vector[1] + data[8] * vector[2],
        )
    )


def resolve_planar_face_frame(component: Any, selection_rule: str) -> PlanarFaceFrame:
    faces = _resolve_planar_face_frames(component)
    if not faces:
        raise RuntimeError(f"No planar faces found for {selection_rule}.")
    if selection_rule == "maximum_z":
        return max(faces, key=lambda item: item.point_mm[2])
    if selection_rule == "minimum_z":
        return min(faces, key=lambda item: item.point_mm[2])
    raise RuntimeError(f"Unsupported planar face selection rule: {selection_rule}")


def _resolve_planar_face_frames(component: Any) -> list[PlanarFaceFrame]:
    faces = []
    transform = component_transform_array(component)
    for face in _component_faces(component):
        local = _planar_face_frame_local(face)
        if local is None:
            continue
        point, normal, u_axis, v_axis = local
        faces.append(
            PlanarFaceFrame(
                face=face,
                point_mm=transform_point_mm(transform, point),
                normal=transform_vector(transform, normal),
                u_axis=transform_vector(transform, u_axis),
                v_axis=transform_vector(transform, v_axis),
            )
        )
    return faces


def resolve_cylindrical_axis(component: Any) -> CylindricalAxis:
    transform = component_transform_array(component)
    for face in _component_faces(component):
        local = _cylindrical_axis_local(face)
        if local is None:
            continue
        point, axis = local
        return CylindricalAxis(
            face=face,
            point_mm=transform_point_mm(transform, point),
            axis=transform_vector(transform, axis),
        )
    raise RuntimeError("No cylindrical face found for component axis resolution.")


def resolve_component_mount_frame(component: Any) -> ComponentMountFrame:
    cylinder = resolve_cylindrical_axis(component)
    planar_faces = _resolve_planar_face_frames(component)
    if not planar_faces:
        raise RuntimeError("No planar end faces found for cylindrical component.")
    end_faces = [face for face in planar_faces if abs(dot(face.normal, cylinder.axis)) > 0.85]
    if not end_faces:
        raise RuntimeError("No planar end face is perpendicular to the cylindrical axis.")
    bottom = min(end_faces, key=lambda face: dot(face.point_mm, cylinder.axis))
    native_axis = cylinder.axis
    if dot(native_axis, bottom.normal) > 0:
        native_axis = (-native_axis[0], -native_axis[1], -native_axis[2])
    source_u = normalize(bottom.u_axis)
    source_v = normalize(cross(native_axis, source_u))
    source_u = normalize(cross(source_v, native_axis))
    return ComponentMountFrame(
        bottom_face=bottom,
        native_axis=native_axis,
        source_u=source_u,
        source_v=source_v,
    )


def build_mounting_transform(
    component: Any,
    mount_frame: ComponentMountFrame,
    target_face: PlanarFaceFrame,
    u_offset_mm: float,
    v_offset_mm: float,
) -> tuple[list[float], dict[str, Any]]:
    current = component_transform_array(component)
    current_rotation = current[:9]
    source_origin_local = _assembly_point_to_component_local(current, mount_frame.bottom_face.point_mm)
    source_axis_local = _assembly_vector_to_component_local(current_rotation, mount_frame.native_axis)
    source_u_local = _assembly_vector_to_component_local(current_rotation, mount_frame.source_u)
    source_v_local = normalize(cross(source_axis_local, source_u_local))
    source_u_local = normalize(cross(source_v_local, source_axis_local))

    target_origin = local_uv_to_world(target_face, u_offset_mm, v_offset_mm)
    target_u = normalize(target_face.u_axis)
    target_axis = normalize(target_face.normal)
    target_v = normalize(cross(target_axis, target_u))
    target_u = normalize(cross(target_v, target_axis))

    rotation = _basis_mapping(
        (source_u_local, source_v_local, source_axis_local),
        (target_u, target_v, target_axis),
    )
    rotated_source_origin_m = _matrix_vector(rotation, tuple(mm_to_m(value) for value in source_origin_local))
    target_origin_m = tuple(mm_to_m(value) for value in target_origin)
    translation_m = (
        target_origin_m[0] - rotated_source_origin_m[0],
        target_origin_m[1] - rotated_source_origin_m[1],
        target_origin_m[2] - rotated_source_origin_m[2],
    )
    data = [
        rotation[0][0],
        rotation[0][1],
        rotation[0][2],
        rotation[1][0],
        rotation[1][1],
        rotation[1][2],
        rotation[2][0],
        rotation[2][1],
        rotation[2][2],
        translation_m[0],
        translation_m[1],
        translation_m[2],
        1.0,
        0.0,
        0.0,
        0.0,
    ]
    final_axis = transform_vector(data, source_axis_local)
    final_bottom = transform_point_mm(data, source_origin_local)
    distance = dot(
        (
            final_bottom[0] - target_origin[0],
            final_bottom[1] - target_origin[1],
            final_bottom[2] - target_origin[2],
        ),
        target_face.normal,
    )
    debug = {
        "plate_top_face": _frame_debug(target_face),
        "native_axis": _round_tuple(mount_frame.native_axis),
        "resolved_bottom_face_point": _round_tuple(mount_frame.bottom_face.point_mm),
        "requested_uv_mm": (u_offset_mm, v_offset_mm),
        "calculated_assembly_position": _round_tuple(target_origin),
        "final_transformed_axis": _round_tuple(final_axis),
        "bottom_face_to_plate_face_distance_mm": distance,
    }
    return data, debug


def select_face(face: Any, append: bool = False) -> bool:
    for name, args in (
        ("Select4", (append, None)),
        ("Select2", (append, 0)),
        ("Select", (append,)),
    ):
        method = getattr(face, name, None)
        if method is None:
            continue
        try:
            return bool(method(*args))
        except Exception:
            continue
    return False


def _component_faces(component: Any) -> list[Any]:
    bodies = _component_bodies(component)
    faces: list[Any] = []
    for body in bodies:
        body_faces = _body_faces(body)
        faces.extend(body_faces)
    return faces


def _component_bodies(component: Any) -> list[Any]:
    for name, args in (
        ("GetBodies3", (0, None)),
        ("GetBodies2", (0,)),
        ("GetBodies", ()),
    ):
        method = getattr(component, name, None)
        if method is None:
            continue
        try:
            bodies = method(*args)
        except Exception:
            continue
        if bodies:
            return list(bodies)
    model = getattr(component, "GetModelDoc2", lambda: None)()
    if model is not None:
        body = getattr(model, "GetBodies2", lambda *_args: None)(0, True)
        if body:
            return list(body)
    raise RuntimeError("Could not enumerate component bodies.")


def _body_faces(body: Any) -> list[Any]:
    method = getattr(body, "GetFaces", None)
    if method is not None:
        try:
            faces = method()
            if faces:
                return list(faces)
        except Exception:
            pass
    faces = []
    face = getattr(body, "GetFirstFace", lambda: None)()
    while face is not None:
        faces.append(face)
        face = getattr(face, "GetNextFace", lambda: None)()
    return faces


def _planar_face_frame_local(face: Any) -> tuple[Vector3, Vector3, Vector3, Vector3] | None:
    surface = getattr(face, "GetSurface", lambda: None)()
    if surface is None or not _surface_bool(surface, "IsPlane"):
        return None
    params = _surface_params(surface, "PlaneParams")
    point = _face_box_center(face)
    normal = _face_normal(face)
    if params and len(params) >= 6:
        normal = normal or (params[3], params[4], params[5])
    if normal is None:
        raise RuntimeError("Planar face did not expose a normal.")
    frame = _frame_from_normal(point, normal)
    return frame


def _cylindrical_axis_local(face: Any) -> tuple[Vector3, Vector3] | None:
    surface = getattr(face, "GetSurface", lambda: None)()
    if surface is None or not _surface_bool(surface, "IsCylinder"):
        return None
    params = _surface_params(surface, "CylinderParams")
    if not params or len(params) < 6:
        return None
    return (
        (m_to_mm(params[0]), m_to_mm(params[1]), m_to_mm(params[2])),
        normalize((params[3], params[4], params[5])),
    )


def _surface_bool(surface: Any, name: str) -> bool:
    value = getattr(surface, name, None)
    if value is None:
        return False
    return bool(value() if callable(value) else value)


def _surface_params(surface: Any, name: str) -> list[float] | None:
    value = getattr(surface, name, None)
    if value is None:
        return None
    try:
        params = value() if callable(value) else value
    except Exception:
        return None
    return list(params) if params is not None else None


def _face_box_center(face: Any) -> Vector3:
    box = getattr(face, "GetBox", lambda: None)()
    if box and len(box) >= 6:
        return (
            m_to_mm((box[0] + box[3]) / 2.0),
            m_to_mm((box[1] + box[4]) / 2.0),
            m_to_mm((box[2] + box[5]) / 2.0),
        )
    return (0.0, 0.0, 0.0)


def _face_normal(face: Any) -> Vector3 | None:
    value = getattr(face, "Normal", None)
    if callable(value):
        value = value()
    if value and len(value) >= 3:
        return normalize((value[0], value[1], value[2]))
    return None


def _frame_from_normal(point: Vector3, normal: Vector3) -> tuple[Vector3, Vector3, Vector3, Vector3]:
    n_axis = normalize(normal)
    preferred = (1.0, 0.0, 0.0) if abs(n_axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    u_axis = normalize(cross(preferred, n_axis))
    v_axis = normalize(cross(n_axis, u_axis))
    return point, n_axis, u_axis, v_axis


def _basis_mapping(source_columns: tuple[Vector3, Vector3, Vector3], target_columns: tuple[Vector3, Vector3, Vector3]):
    target_rows = tuple(zip(*target_columns))
    return tuple(
        tuple(
            dot(tuple(target_rows[row][k] for k in range(3)), source_columns[col])
            for col in range(3)
        )
        for row in range(3)
    )


def _matrix_vector(matrix: tuple[Vector3, Vector3, Vector3], vector: Vector3) -> Vector3:
    return (dot(matrix[0], vector), dot(matrix[1], vector), dot(matrix[2], vector))


def _assembly_point_to_component_local(data: list[float], point_mm: Vector3) -> Vector3:
    tx = (point_mm[0] - m_to_mm(data[9]), point_mm[1] - m_to_mm(data[10]), point_mm[2] - m_to_mm(data[11]))
    rows = ((data[0], data[1], data[2]), (data[3], data[4], data[5]), (data[6], data[7], data[8]))
    columns = tuple(zip(*rows))
    return tuple(dot(tuple(column), tx) for column in columns)  # type: ignore[return-value]


def _assembly_vector_to_component_local(rotation: list[float], vector: Vector3) -> Vector3:
    rows = ((rotation[0], rotation[1], rotation[2]), (rotation[3], rotation[4], rotation[5]), (rotation[6], rotation[7], rotation[8]))
    columns = tuple(zip(*rows))
    return normalize(tuple(dot(tuple(column), vector) for column in columns))  # type: ignore[return-value]


def _frame_debug(frame: PlanarFaceFrame) -> dict[str, tuple[float, float, float]]:
    return {
        "point": _round_tuple(frame.point_mm),
        "normal": _round_tuple(frame.normal),
        "u": _round_tuple(frame.u_axis),
        "v": _round_tuple(frame.v_axis),
    }


def _round_tuple(values: Vector3) -> tuple[float, float, float]:
    return tuple(round(value, 6) for value in values)  # type: ignore[return-value]
