from __future__ import annotations

import unittest

from parser.rule_parser import parse_prompt_rule_based
from validator.validate_intent import validate_intent


class RuleParserTests(unittest.TestCase):
    def test_cube_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based("create a 50 mm cube")

        self.assertEqual(
            intent,
            {
                "tool_name": "create_cube",
                "parameters": {"side_mm": 50.0},
            },
        )

    def test_block_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based("create a block 100 by 60 by 20 mm")

        self.assertEqual(
            intent,
            {
                "tool_name": "create_block",
                "parameters": {
                    "length_mm": 100.0,
                    "width_mm": 60.0,
                    "height_mm": 20.0,
                },
            },
        )

    def test_cylinder_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based("create cylinder diameter 30 mm height 80 mm")

        self.assertEqual(
            intent,
            {
                "tool_name": "create_cylinder",
                "parameters": {
                    "diameter_mm": 30.0,
                    "height_mm": 80.0,
                },
            },
        )

    def test_export_step_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based("export step as test.step")

        self.assertEqual(
            intent,
            {
                "tool_name": "export_step",
                "parameters": {"filename": "test.step"},
            },
        )

    def test_unparseable_prompt_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            parse_prompt_rule_based("do something vague")

    def test_negative_cube_dimension_is_rejected_by_validator(self) -> None:
        intent = parse_prompt_rule_based("create a -50 mm cube")

        self.assertEqual(intent["parameters"]["side_mm"], -50.0)
        with self.assertRaises(ValueError):
            validate_intent(intent)

    def test_disc_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based("create disc diameter 50 mm thickness 5 mm")

        self.assertEqual(
            intent,
            {
                "tool_name": "create_disc",
                "parameters": {"diameter_mm": 50.0, "thickness_mm": 5.0},
            },
        )

    def test_plate_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based("create plate 100 by 60 by 5 mm")

        self.assertEqual(
            intent,
            {
                "tool_name": "create_plate",
                "parameters": {
                    "length_mm": 100.0,
                    "width_mm": 60.0,
                    "thickness_mm": 5.0,
                },
            },
        )

    def test_tube_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based(
            "create tube outer diameter 50 mm inner diameter 30 mm height 80 mm"
        )

        self.assertEqual(
            intent,
            {
                "tool_name": "create_tube",
                "parameters": {
                    "outer_diameter_mm": 50.0,
                    "inner_diameter_mm": 30.0,
                    "height_mm": 80.0,
                },
            },
        )

    def test_hollow_cylinder_prompt_parses_as_tube(self) -> None:
        intent = parse_prompt_rule_based(
            "create hollow cylinder outer diameter 50 mm inner diameter 30 mm height 80 mm"
        )

        self.assertEqual(intent["tool_name"], "create_tube")
        self.assertEqual(intent["parameters"]["outer_diameter_mm"], 50.0)

    def test_plate_with_hole_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based(
            "create plate 100 by 60 by 5 mm with hole diameter 20 mm"
        )

        self.assertEqual(
            intent,
            {
                "tool_name": "create_plate_with_hole",
                "parameters": {
                    "length_mm": 100.0,
                    "width_mm": 60.0,
                    "thickness_mm": 5.0,
                    "hole_diameter_mm": 20.0,
                },
            },
        )

    def test_cone_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based("create cone base diameter 50 mm height 80 mm")

        self.assertEqual(
            intent,
            {
                "tool_name": "create_cone",
                "parameters": {"base_diameter_mm": 50.0, "height_mm": 80.0},
            },
        )

    def test_sphere_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based("make a ball of diameter 50 mm")

        self.assertEqual(
            intent,
            {
                "tool_name": "create_sphere",
                "parameters": {"diameter_mm": 50.0},
            },
        )

    def test_torus_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based(
            "create torus major diameter 80 mm minor diameter 20 mm"
        )

        self.assertEqual(
            intent,
            {
                "tool_name": "create_torus",
                "parameters": {"major_diameter_mm": 80.0, "minor_diameter_mm": 20.0},
            },
        )

    def test_negative_block_dimension_is_rejected_by_validator(self) -> None:
        intent = parse_prompt_rule_based("create a block 100 by -60 by 20 mm")

        self.assertEqual(intent["parameters"]["width_mm"], -60.0)
        with self.assertRaises(ValueError):
            validate_intent(intent)

    def test_negative_cylinder_dimension_is_rejected_by_validator(self) -> None:
        intent = parse_prompt_rule_based("create cylinder diameter -30 mm height 80 mm")

        self.assertEqual(intent["parameters"]["diameter_mm"], -30.0)
        with self.assertRaises(ValueError):
            validate_intent(intent)

    def test_base_plate_with_cylinders_assembly_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based("create an assembly with a base plate and two cylinders")

        self.assertEqual(intent["tool_name"], "create_assembly")
        self.assertEqual(intent["parameters"]["assembly_type"], "base_plate_with_cylinders")

    def test_tube_with_end_discs_assembly_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based("create an assembly with a tube and two end discs")

        self.assertEqual(intent["tool_name"], "create_assembly")
        self.assertEqual(intent["parameters"]["assembly_type"], "tube_with_two_end_discs")

    def test_shaft_with_wheels_assembly_prompt_parses_correctly(self) -> None:
        intent = parse_prompt_rule_based("make axle with two wheels")

        self.assertEqual(intent["tool_name"], "create_assembly")
        self.assertEqual(intent["parameters"]["assembly_type"], "simple_shaft_with_two_wheels")
