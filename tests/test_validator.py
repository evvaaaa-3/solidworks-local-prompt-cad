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
