from __future__ import annotations

import unittest

from parser.rule_parser import parse_prompt_rule_based


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
