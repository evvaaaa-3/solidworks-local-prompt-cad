from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cad_tools.assemblies import execute_assembly_plan
from cad_tools.assembly_planner import (
    AssemblyPlan,
    ComponentInstanceSpec,
    ComponentSpec,
    ConstraintSpec,
    FeatureSpec,
    build_assembly_plan,
    validate_assembly_plan,
)
from cad_tools.component_factory import ComponentBuildResult, create_component_part


DEFAULT_PARAMETERS = {
    "base_length_mm": 120.0,
    "base_width_mm": 80.0,
    "base_thickness_mm": 8.0,
    "post_diameter_mm": 20.0,
    "post_height_mm": 40.0,
    "post_count": 2,
    "tube_outer_diameter_mm": 50.0,
    "tube_inner_diameter_mm": 30.0,
    "tube_height_mm": 100.0,
    "cap_diameter_mm": 50.0,
    "cap_thickness_mm": 6.0,
    "cap_count": 2,
    "shaft_diameter_mm": 12.0,
    "shaft_length_mm": 120.0,
    "wheel_diameter_mm": 45.0,
    "wheel_thickness_mm": 12.0,
    "wheel_count": 2,
}


class AssemblyPlannerTests(unittest.TestCase):
    def test_component_and_feature_specs_create(self) -> None:
        feature = FeatureSpec(
            type="through_hole",
            dimensions={"diameter_mm": 10.0},
            name="mounting_hole",
        )
        component = ComponentSpec(
            id="plate",
            type="plate_with_hole",
            dimensions={
                "length_mm": 100.0,
                "width_mm": 60.0,
                "thickness_mm": 5.0,
                "hole_diameter_mm": 10.0,
            },
            features=(feature,),
        )

        self.assertEqual(component.id, "plate")
        self.assertEqual(component.features[0].type, "through_hole")

    def test_base_plate_plan_has_plate_and_two_post_instances(self) -> None:
        plan = build_assembly_plan("base_plate_with_cylinders", DEFAULT_PARAMETERS)

        self.assertEqual({component.type for component in plan.components}, {"plate", "cylinder"})
        self.assertEqual([instance.id for instance in plan.instances], [
            "base_plate_1",
            "post_left",
            "post_right",
        ])

    def test_tube_plan_has_tube_and_two_cap_instances(self) -> None:
        plan = build_assembly_plan("tube_with_two_end_discs", DEFAULT_PARAMETERS)

        self.assertEqual({component.type for component in plan.components}, {"tube", "disc"})
        self.assertEqual([instance.id for instance in plan.instances], ["tube_1", "cap_a", "cap_b"])

    def test_shaft_plan_has_shaft_and_two_wheel_instances(self) -> None:
        plan = build_assembly_plan("simple_shaft_with_two_wheels", DEFAULT_PARAMETERS)

        self.assertEqual({component.type for component in plan.components}, {"shaft", "wheel"})
        self.assertEqual(
            [instance.id for instance in plan.instances],
            ["shaft_1", "wheel_left", "wheel_right"],
        )

    def test_constraints_reference_valid_components_or_instances(self) -> None:
        plan = build_assembly_plan("tube_with_two_end_discs", DEFAULT_PARAMETERS)

        validate_assembly_plan(plan)

    def test_plan_validation_rejects_unknown_instance_component(self) -> None:
        plan = AssemblyPlan(
            assembly_type="bad",
            components=(
                ComponentSpec("plate", "plate", {"length_mm": 1, "width_mm": 1, "thickness_mm": 1}),
            ),
            instances=(
                ComponentInstanceSpec("missing", "missing_component", "missing", (0, 0, 0)),
            ),
            constraints=(),
            output_filename="bad.SLDASM",
        )

        with self.assertRaisesRegex(ValueError, "unknown component"):
            validate_assembly_plan(plan)

    def test_plan_validation_rejects_bad_constraint_reference(self) -> None:
        plan = AssemblyPlan(
            assembly_type="bad",
            components=(
                ComponentSpec("plate", "plate", {"length_mm": 1, "width_mm": 1, "thickness_mm": 1}),
            ),
            instances=(
                ComponentInstanceSpec("plate_1", "plate", "plate_1", (0, 0, 0)),
            ),
            constraints=(ConstraintSpec("fixed", "not_real"),),
            output_filename="bad.SLDASM",
        )

        with self.assertRaisesRegex(ValueError, "unknown component/instance"):
            validate_assembly_plan(plan)


class ComponentFactoryTests(unittest.TestCase):
    def test_component_factory_maps_plate(self) -> None:
        component = ComponentSpec(
            id="plate",
            type="plate",
            dimensions={"length_mm": 100, "width_mm": 60, "thickness_mm": 5},
        )
        with patch("cad_tools.component_factory.primitives.create_plate") as create_plate:
            create_plate.return_value = {"filepath": "plate.SLDPRT"}
            result = create_component_part(component, dry_run=False)

        create_plate.assert_called_once_with(100, 60, 5, dry_run=False)
        self.assertEqual(result.filepath, "plate.SLDPRT")

    def test_component_factory_maps_shaft_to_cylinder(self) -> None:
        component = ComponentSpec(
            id="shaft",
            type="shaft",
            dimensions={"diameter_mm": 12, "length_mm": 120},
        )
        with patch("cad_tools.component_factory.primitives.create_cylinder") as create_cylinder:
            create_cylinder.return_value = {"filepath": "shaft.SLDPRT"}
            result = create_component_part(component, dry_run=False)

        create_cylinder.assert_called_once_with(12, 120, dry_run=False)
        self.assertEqual(result.filepath, "shaft.SLDPRT")


class AssemblyExecutorTests(unittest.TestCase):
    def test_generic_executor_with_mocked_solidworks_api(self) -> None:
        plan = build_assembly_plan("base_plate_with_cylinders", DEFAULT_PARAMETERS)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "base_plate_with_cylinders.SLDASM"

            def fake_save(_assembly_model, _filepath):
                output_path.write_text("assembly", encoding="utf-8")
                return {"status": "success", "filepath": str(output_path)}

            component_results = {
                "base_plate": ComponentBuildResult(
                    "base_plate", "base_plate", "plate", "base", "plate.SLDPRT", "plate.SLDPRT", 1, True
                ),
                "post": ComponentBuildResult(
                    "post", "post", "cylinder", "post", "post.SLDPRT", "post.SLDPRT", 2, True
                ),
            }

            with patch("cad_tools.assemblies.create_components_for_plan", return_value=component_results), \
                patch("cad_tools.assemblies.connect_solidworks", return_value=object()), \
                patch("cad_tools.assemblies.create_new_assembly", return_value=object()), \
                patch("cad_tools.assemblies.insert_component", return_value=object()) as insert_component, \
                patch("cad_tools.assemblies.set_component_position"), \
                patch("cad_tools.assemblies.fix_component"), \
                patch("cad_tools.assemblies.save_assembly", side_effect=fake_save):
                result = execute_assembly_plan(plan, dry_run=False)

        self.assertTrue(result["success"])
        self.assertEqual(result["operation"], "create_assembly")
        self.assertEqual(len(result["instances"]), 3)
        self.assertTrue(result["placement_fallback_used"])
        self.assertGreaterEqual(len(result["constraints_planned"]), 1)
        self.assertEqual(insert_component.call_count, 3)


if __name__ == "__main__":
    unittest.main()
