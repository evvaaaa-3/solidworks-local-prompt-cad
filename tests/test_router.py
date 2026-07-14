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
            result["status"],
            "dry_run_success",
        )
        self.assertEqual(result["tool"], "create_cube")
        self.assertEqual(result["dimensions_mm"], {"side_mm": 50.0})

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

    def test_dry_run_routes_disc(self) -> None:
        intent = validate_intent(
            {"tool_name": "create_disc", "parameters": {"diameter_mm": 50, "thickness_mm": 5}}
        )

        result = route_intent(intent, dry_run=True)

        self.assertEqual(result["tool"], "create_disc")
        self.assertEqual(result["status"], "dry_run_success")

    def test_dry_run_routes_plate(self) -> None:
        intent = validate_intent(
            {
                "tool_name": "create_plate",
                "parameters": {"length_mm": 100, "width_mm": 60, "thickness_mm": 5},
            }
        )

        result = route_intent(intent, dry_run=True)

        self.assertEqual(result["tool"], "create_plate")

    def test_dry_run_routes_tube(self) -> None:
        intent = validate_intent(
            {
                "tool_name": "create_tube",
                "parameters": {
                    "outer_diameter_mm": 50,
                    "inner_diameter_mm": 30,
                    "height_mm": 80,
                },
            }
        )

        result = route_intent(intent, dry_run=True)

        self.assertEqual(result["tool"], "create_tube")

    def test_dry_run_routes_plate_with_hole(self) -> None:
        intent = validate_intent(
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

        result = route_intent(intent, dry_run=True)

        self.assertEqual(result["tool"], "create_plate_with_hole")

    def test_dry_run_routes_cone(self) -> None:
        intent = validate_intent(
            {
                "tool_name": "create_cone",
                "parameters": {"base_diameter_mm": 50, "height_mm": 80},
            }
        )

        result = route_intent(intent, dry_run=True)

        self.assertEqual(result["tool"], "create_cone")
        self.assertEqual(result["feature_type"], "dry_run")

    def test_dry_run_routes_sphere(self) -> None:
        intent = validate_intent(
            {"tool_name": "create_sphere", "parameters": {"diameter_mm": 50}}
        )

        result = route_intent(intent, dry_run=True)

        self.assertEqual(result["tool"], "create_sphere")

    def test_dry_run_routes_torus(self) -> None:
        intent = validate_intent(
            {
                "tool_name": "create_torus",
                "parameters": {"major_diameter_mm": 80, "minor_diameter_mm": 20},
            }
        )

        result = route_intent(intent, dry_run=True)

        self.assertEqual(result["tool"], "create_torus")

    def test_router_routes_create_assembly(self) -> None:
        intent = validate_intent(
            {
                "tool_name": "create_assembly",
                "parameters": {"assembly_type": "base_plate_with_cylinders"},
            }
        )

        with patch("router.tool_router.create_assembly") as create_assembly:
            create_assembly.return_value = {"success": True, "operation": "create_assembly"}
            result = route_intent(intent, dry_run=False)

        self.assertEqual(result, {"success": True, "operation": "create_assembly"})
        create_assembly.assert_called_once()
        _, kwargs = create_assembly.call_args
        self.assertEqual(kwargs["assembly_type"], "base_plate_with_cylinders")
        self.assertFalse(kwargs["dry_run"])
