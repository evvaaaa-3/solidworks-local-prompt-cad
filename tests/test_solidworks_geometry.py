from __future__ import annotations

import unittest

from solidworks_api.geometry import (
    build_mounting_transform,
    resolve_component_mount_frame,
    resolve_planar_face_frame,
    select_face,
    transform_point_mm,
    transform_vector,
)


class SolidWorksGeometryTests(unittest.TestCase):
    def test_resolves_plate_top_face_frame_from_component_faces(self) -> None:
        plate = FakeComponent(
            [
                FakeFace("plane", z_mm=0.0, normal=(0.0, 0.0, -1.0), box=(-60, -40, 0, 60, 40, 0)),
                FakeFace("plane", z_mm=8.0, normal=(0.0, 0.0, 1.0), box=(-60, -40, 8, 60, 40, 8)),
            ]
        )

        frame = resolve_planar_face_frame(plate, "maximum_z")

        self.assertEqual(frame.point_mm, (0.0, 0.0, 8.0))
        self.assertEqual(frame.normal, (0.0, 0.0, 1.0))

    def test_mounting_transform_maps_cylinder_bottom_frame_to_plate_face_uv(self) -> None:
        plate = FakeComponent(
            [
                FakeFace("plane", z_mm=0.0, normal=(0.0, 0.0, -1.0), box=(-60, -40, 0, 60, 40, 0)),
                FakeFace("plane", z_mm=8.0, normal=(0.0, 0.0, 1.0), box=(-60, -40, 8, 60, 40, 8)),
            ]
        )
        cylinder = FakeComponent(
            [
                FakeFace("plane", z_mm=0.0, normal=(0.0, 0.0, -1.0), box=(-10, -10, 0, 10, 10, 0)),
                FakeFace("plane", z_mm=40.0, normal=(0.0, 0.0, 1.0), box=(-10, -10, 40, 10, 10, 40)),
                FakeFace("cylinder", axis=(0.0, 0.0, 1.0)),
            ]
        )
        plate_top = resolve_planar_face_frame(plate, "maximum_z")
        mount = resolve_component_mount_frame(cylinder)

        data, debug = build_mounting_transform(cylinder, mount, plate_top, -30.0, 0.0)

        final_bottom = transform_point_mm(data, (0.0, 0.0, 0.0))
        final_axis = transform_vector(data, (0.0, 0.0, 1.0))
        self.assertAlmostEqual(debug["bottom_face_to_plate_face_distance_mm"], 0.0)
        self.assertEqual(final_bottom, (0.0, 30.0, 8.0))
        self.assertEqual(final_axis, (0.0, 0.0, 1.0))

    def test_select_face_uses_real_face_methods(self) -> None:
        face = FakeFace("plane", z_mm=0.0, normal=(0.0, 0.0, 1.0), box=(0, 0, 0, 1, 1, 0))

        self.assertTrue(select_face(face, append=True))
        self.assertEqual(face.select_calls, [(True, None)])


class FakeComponent:
    def __init__(self, faces):
        self.Transform2 = FakeTransform()
        self._bodies = [FakeBody(faces)]

    def GetBodies3(self, *_args):
        return self._bodies


class FakeTransform:
    def __init__(self):
        self.ArrayData = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]


class FakeBody:
    def __init__(self, faces):
        self._faces = faces

    def GetFaces(self):
        return self._faces


class FakeFace:
    def __init__(
        self,
        kind: str,
        *,
        z_mm: float = 0.0,
        normal=(0.0, 0.0, 1.0),
        axis=(0.0, 0.0, 1.0),
        box=(-1.0, -1.0, 0.0, 1.0, 1.0, 0.0),
    ):
        self._surface = FakeSurface(kind, z_mm=z_mm, normal=normal, axis=axis)
        self._box = tuple(value / 1000.0 for value in box)
        self.select_calls = []

    def GetSurface(self):
        return self._surface

    def GetBox(self):
        return self._box

    def Select4(self, append, data):
        self.select_calls.append((append, data))
        return True


class FakeSurface:
    def __init__(self, kind: str, *, z_mm: float, normal, axis):
        self.kind = kind
        self.z_m = z_mm / 1000.0
        self.normal = normal
        self.axis = axis

    def IsPlane(self):
        return self.kind == "plane"

    def IsCylinder(self):
        return self.kind == "cylinder"

    def PlaneParams(self):
        return [0.0, 0.0, self.z_m, self.normal[0], self.normal[1], self.normal[2]]

    def CylinderParams(self):
        return [0.0, 0.0, 0.0, self.axis[0], self.axis[1], self.axis[2], 0.01]


if __name__ == "__main__":
    unittest.main()
