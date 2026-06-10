from __future__ import annotations

import unittest

from router.tool_router import route_intent
from validator.validate_intent import validate_intent


class RouterTests(unittest.TestCase):
    def test_dry_run_route_for_cube_returns_success(self) -> None:
        intent = validate_intent(
            {"tool_name": "create_cube", "parameters": {"side_mm": 50}}
        )

        result = route_intent(intent, dry_run=True)

        self.assertEqual(
            result,
            {
                "status": "dry_run_success",
                "tool": "create_cube",
                "parameters": {"side_mm": 50.0},
            },
        )

    def test_dry_run_route_does_not_call_solidworks(self) -> None:
        intent = validate_intent(
            {"tool_name": "create_cube", "parameters": {"side_mm": 25}}
        )

        result = route_intent(intent, dry_run=True)

        self.assertEqual(result["status"], "dry_run_success")
        self.assertEqual(result["tool"], "create_cube")
