from __future__ import annotations

import math
import unittest

from cad_tools.cad_schemas import TransformSpec
from cad_tools.face_placement import (
    FacePlacementSpec,
    dot,
    face_relative_component_origin,
    frame_from_normal,
    local_uv_to_world,
    normalize,
    rotation_align_vectors,
    top_face_frame_from_box,
)


class FacePlacementTests(unittest.TestCase):
    def test_frame_from_normal_is_orthonormal(self) -> None:
        frame = frame_from_normal((0.0, 0.0, 0.0), (0.0, 0.0, 5.0))

        self.assertAlmostEqual(dot(frame.normal, frame.u_axis), 0.0)
        self.assertAlmostEqual(dot(frame.normal, frame.v_axis), 0.0)
        self.assertAlmostEqual(dot(frame.u_axis, frame.v_axis), 0.0)
        self.assertEqual(frame.normal, (0.0, 0.0, 1.0))

    def test_normalize_rejects_zero_vector(self) -> None:
        with self.assertRaises(ValueError):
            normalize((0.0, 0.0, 0.0))

    def test_local_uv_to_world_positions_lie_on_same_plane(self) -> None:
        frame = top_face_frame_from_box(TransformSpec())
        left = local_uv_to_world(frame, -25.0, 0.0)
        right = local_uv_to_world(frame, 25.0, 0.0)

        self.assertNotEqual(left, right)
        self.assertEqual(left[2], right[2])
        self.assertEqual(left[2], frame.origin[2])

    def test_normal_offset_moves_along_normal(self) -> None:
        frame = top_face_frame_from_box(TransformSpec())

        self.assertEqual(local_uv_to_world(frame, 0.0, 0.0, 10.0), (0.0, 0.0, 10.0))

    def test_rotation_align_vectors_maps_z_to_x(self) -> None:
        matrix = rotation_align_vectors((0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
        mapped = (
            matrix[0][2],
            matrix[1][2],
            matrix[2][2],
        )

        self.assertAlmostEqual(mapped[0], 1.0)
        self.assertAlmostEqual(mapped[1], 0.0)
        self.assertAlmostEqual(mapped[2], 0.0)

    def test_component_base_origin_convention_for_negative_z_axis(self) -> None:
        frame = top_face_frame_from_box(TransformSpec())
        placement = FacePlacementSpec(
            target_instance_id="plate",
            target_reference="top_face",
            u_offset_mm=0.0,
            v_offset_mm=0.0,
            source_axis="-Z",
            component_axis_length_mm=40.0,
        )

        self.assertEqual(face_relative_component_origin(frame, placement), (0.0, 0.0, 40.0))

    def test_rotated_plate_positions_rotate_with_face(self) -> None:
        transform = TransformSpec(rotation_y=90.0)
        frame = top_face_frame_from_box(transform)
        left = local_uv_to_world(frame, -25.0, 0.0)
        right = local_uv_to_world(frame, 25.0, 0.0)

        self.assertNotEqual(left, right)
        self.assertAlmostEqual(dot(left, frame.normal), dot(right, frame.normal))
        self.assertAlmostEqual(frame.normal[0], 1.0)

    def test_face_relative_origin_rotates_with_plate_normal(self) -> None:
        frame = top_face_frame_from_box(TransformSpec(rotation_y=90.0))
        placement = FacePlacementSpec(
            target_instance_id="plate",
            target_reference="top_face",
            u_offset_mm=0.0,
            v_offset_mm=0.0,
            source_axis="-Z",
            component_axis_length_mm=40.0,
        )
        origin = face_relative_component_origin(frame, placement)

        self.assertAlmostEqual(origin[0], 40.0)
        self.assertAlmostEqual(origin[1], 0.0)
        self.assertAlmostEqual(origin[2], 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
