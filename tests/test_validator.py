from __future__ import annotations

import unittest

from validator.validate_intent import validate_intent


class ValidatorTests(unittest.TestCase):
    def test_valid_cube_passes(self) -> None:
        validated = validate_intent(
            {"tool_name": "create_cube", "parameters": {"side_mm": 50}}
        )

        self.assertEqual(validated.tool_name, "create_cube")
        self.assertEqual(validated.parameters.side_mm, 50.0)

    def test_negative_dimension_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_intent({"tool_name": "create_cube", "parameters": {"side_mm": -1}})

    def test_unsupported_tool_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_intent({"tool_name": "loft_magic", "parameters": {}})

    def test_unsafe_filename_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_intent(
                {
                    "tool_name": "export_step",
                    "parameters": {"filename": "..\\unsafe.step"},
                }
            )

    def test_non_step_filename_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_intent(
                {"tool_name": "export_step", "parameters": {"filename": "cube.txt"}}
            )

    def test_valid_disc_passes(self) -> None:
        validated = validate_intent(
            {
                "tool_name": "create_disc",
                "parameters": {"diameter_mm": 50, "thickness_mm": 5},
            }
        )

        self.assertEqual(validated.tool_name, "create_disc")

    def test_valid_plate_passes(self) -> None:
        validated = validate_intent(
            {
                "tool_name": "create_plate",
                "parameters": {"length_mm": 100, "width_mm": 60, "thickness_mm": 5},
            }
        )

        self.assertEqual(validated.tool_name, "create_plate")

    def test_valid_tube_passes(self) -> None:
        validated = validate_intent(
            {
                "tool_name": "create_tube",
                "parameters": {
                    "outer_diameter_mm": 50,
                    "inner_diameter_mm": 30,
                    "height_mm": 80,
                },
            }
        )

        self.assertEqual(validated.tool_name, "create_tube")

    def test_invalid_tube_inner_greater_than_outer_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_intent(
                {
                    "tool_name": "create_tube",
                    "parameters": {
                        "outer_diameter_mm": 30,
                        "inner_diameter_mm": 30,
                        "height_mm": 80,
                    },
                }
            )

    def test_valid_plate_with_hole_passes(self) -> None:
        validated = validate_intent(
            {
                "tool_name": "create_plate_with_hole",
                "parameters": {
                    "length_mm": 100,
                    "width_mm": 60,
                    "thickness_mm": 5,
                    "hole_diameter_mm": 20,
                },
            }
        )

        self.assertEqual(validated.tool_name, "create_plate_with_hole")

    def test_invalid_plate_with_hole_too_large_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_intent(
                {
                    "tool_name": "create_plate_with_hole",
                    "parameters": {
                        "length_mm": 100,
                        "width_mm": 60,
                        "thickness_mm": 5,
                        "hole_diameter_mm": 60,
                    },
                }
            )

    def test_negative_cone_dimension_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_intent(
                {
                    "tool_name": "create_cone",
                    "parameters": {"base_diameter_mm": -50, "height_mm": 80},
                }
            )

    def test_negative_sphere_diameter_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_intent(
                {"tool_name": "create_sphere", "parameters": {"diameter_mm": -50}}
            )

    def test_invalid_torus_geometry_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_intent(
                {
                    "tool_name": "create_torus",
                    "parameters": {"major_diameter_mm": 20, "minor_diameter_mm": 20},
                }
            )

    def test_valid_assembly_intent_fills_defaults(self) -> None:
        validated = validate_intent(
            {
                "tool_name": "create_assembly",
                "parameters": {"assembly_type": "base_plate_with_cylinders"},
            }
        )

        self.assertEqual(validated.tool_name, "create_assembly")
        self.assertEqual(validated.parameters.assembly_type, "base_plate_with_cylinders")
        self.assertEqual(validated.parameters.base_length_mm, 120.0)
        self.assertEqual(validated.parameters.post_count, 2)

    def test_invalid_assembly_type_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_intent(
                {
                    "tool_name": "create_assembly",
                    "parameters": {"assembly_type": "unsupported_assembly"},
                }
            )
