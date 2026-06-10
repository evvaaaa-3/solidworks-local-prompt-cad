from __future__ import annotations

import unittest
from unittest.mock import patch

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

        with patch("cad_tools.primitives.connect_solidworks") as connect_solidworks:
            result = route_intent(intent, dry_run=True)

        self.assertEqual(result["status"], "dry_run_success")
        self.assertEqual(result["tool"], "create_cube")
        connect_solidworks.assert_not_called()

    def test_router_passes_dry_run_false_to_tool(self) -> None:
        intent = validate_intent(
            {"tool_name": "create_cube", "parameters": {"side_mm": 10}}
        )

        with patch("router.tool_router.create_cube") as create_cube:
            create_cube.return_value = {"status": "success"}
            result = route_intent(intent, dry_run=False)

        self.assertEqual(result, {"status": "success"})
        create_cube.assert_called_once_with(side_mm=10.0, dry_run=False)
