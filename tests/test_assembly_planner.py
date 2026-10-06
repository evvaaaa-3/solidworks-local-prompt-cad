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
from cad_tools.transforms import transform_rotation_rad, transform_translation_m


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

    def test_base_plate_post_transforms_are_distinct_and_inside_plate_bounds(self) -> None:
        plan = build_assembly_plan("base_plate_with_cylinders", DEFAULT_PARAMETERS)
        instances = {instance.id: instance for instance in plan.instances}

        left = instances["post_left"].effective_transform()
        right = instances["post_right"].effective_transform()
        plate = next(component for component in plan.components if component.id == "base_plate")
        post = next(component for component in plan.components if component.id == "post")
        half_length = plate.dimensions["length_mm"] / 2.0
        radius = post.dimensions["diameter_mm"] / 2.0

        self.assertIsNot(left, right)
        self.assertNotEqual(left.translation_x, right.translation_x)
        self.assertEqual(left.translation_z, post.dimensions["height_mm"])
        self.assertEqual(right.translation_z, post.dimensions["height_mm"])
        self.assertLessEqual(abs(left.translation_x) + radius, half_length)
        self.assertLessEqual(abs(right.translation_x) + radius, half_length)

    def test_base_plate_transform_unit_conversions(self) -> None:
        plan = build_assembly_plan("base_plate_with_cylinders", DEFAULT_PARAMETERS)
        transform = next(instance for instance in plan.instances if instance.id == "post_right").effective_transform()

        self.assertEqual(transform_translation_m(transform)[2], 0.04)
        self.assertEqual(transform_rotation_rad(transform), (0.0, 0.0, 0.0))

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

    def test_flanged_shaft_demo_plan_uses_generic_constraints(self) -> None:
        plan = build_assembly_plan("flanged_shaft_assembly", DEFAULT_PARAMETERS)

        self.assertEqual({component.id for component in plan.components}, {"shaft", "flange", "hub"})
        self.assertIn("distance", {constraint.type for constraint in plan.constraints})
        self.assertFalse(any(constraint.type == "coordinate_place" for constraint in plan.constraints))

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

    def test_plan_validation_rejects_missing_constraint_value(self) -> None:
        plan = AssemblyPlan(
            assembly_type="bad",
            components=(
                ComponentSpec("plate", "plate", {"length_mm": 1, "width_mm": 1, "thickness_mm": 1}),
            ),
            instances=(
                ComponentInstanceSpec("plate_1", "plate", "plate_1", (0, 0, 0)),
                ComponentInstanceSpec("plate_2", "plate", "plate_2", (1, 0, 0)),
            ),
            constraints=(ConstraintSpec("distance", "plate_1", "top_face", "plate_2", "bottom_face"),),
            output_filename="bad.SLDASM",
        )

        with self.assertRaisesRegex(ValueError, "requires a value"):
            validate_assembly_plan(plan)


class ComponentFactoryTests(unittest.TestCase):
    def test_component_factory_maps_plate(self) -> None:
        component = ComponentSpec(
            id="plate",
            type="plate",
            dimensions={"length_mm": 100, "width_mm": 60, "thickness_mm": 5},
        )
        with patch("cad_tools.component_factory.execute_part_plan") as execute_part_plan:
            execute_part_plan.return_value = {"filepath": "plate.SLDPRT", "features_executed": ["base_plate"]}
            result = create_component_part(component, dry_run=False)

        execute_part_plan.assert_called_once()
        self.assertEqual(execute_part_plan.call_args.args[0].base_feature.feature_type, "boss_extrude")
        self.assertEqual(result.filepath, "plate.SLDPRT")
        self.assertEqual(result.features_executed, ("base_plate",))

    def test_component_factory_maps_shaft_to_cylinder(self) -> None:
        component = ComponentSpec(
            id="shaft",
            type="shaft",
            dimensions={"diameter_mm": 12, "length_mm": 120},
        )
        with patch("cad_tools.component_factory.execute_part_plan") as execute_part_plan:
            execute_part_plan.return_value = {"filepath": "shaft.SLDPRT", "features_executed": ["shaft_body"]}
            result = create_component_part(component, dry_run=False)

        execute_part_plan.assert_called_once()
        self.assertEqual(execute_part_plan.call_args.args[0].base_feature.feature_id, "shaft_body")
        self.assertEqual(result.filepath, "shaft.SLDPRT")


class AssemblyExecutorTests(unittest.TestCase):
    def test_generic_executor_with_mocked_solidworks_api(self) -> None:
        plan = build_assembly_plan("base_plate_with_cylinders", DEFAULT_PARAMETERS)
        assembly_model = FakeAssemblyModel()

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
                patch("cad_tools.assemblies.create_new_assembly", return_value=assembly_model), \
                patch("cad_tools.assemblies.insert_component", side_effect=lambda *_args: FakeComponent()) as insert_component, \
                patch("cad_tools.assemblies.set_component_transform", side_effect=_fake_transform_report), \
                patch("cad_tools.assemblies.fix_component"), \
                patch("cad_tools.assemblies.save_assembly", side_effect=fake_save):
                result = execute_assembly_plan(plan, dry_run=False)

        self.assertFalse(result["success"])
        self.assertEqual(result["operation"], "create_assembly")
        self.assertEqual(len(result["instances"]), 3)
        self.assertFalse(result["placement_fallback_used"])
        self.assertGreaterEqual(len(result["constraints_planned"]), 1)
        self.assertGreaterEqual(len(result["constraints_failed"]), 1)
        self.assertEqual(insert_component.call_count, 3)
        self.assertEqual(len(result["inserted_components"]), 3)
        self.assertIn("message", result["constraints_failed"][0])

    def test_executor_maps_duplicate_part_instances_by_instance_id(self) -> None:
        plan = build_assembly_plan("base_plate_with_cylinders", DEFAULT_PARAMETERS)
        assembly_model = FakeAssemblyModel()
        fake_components = [FakeComponent("plate"), FakeComponent("left"), FakeComponent("right")]

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

            requested_actuals = [
                (0.0, 0.0, 0.0),
                (-30.0, 0.0, 40.0),
                (30.0, 0.0, 40.0),
            ]

            with patch("cad_tools.assemblies.create_components_for_plan", return_value=component_results), \
                patch("cad_tools.assemblies.connect_solidworks", return_value=object()), \
                patch("cad_tools.assemblies.create_new_assembly", return_value=assembly_model), \
                patch("cad_tools.assemblies.insert_component", side_effect=fake_components), \
                patch("cad_tools.assemblies.get_component_translation_mm", side_effect=requested_actuals), \
                patch("cad_tools.assemblies.set_component_transform") as set_transform, \
                patch("cad_tools.assemblies.fix_component"), \
                patch("cad_tools.assemblies.save_assembly", side_effect=fake_save):
                result = execute_assembly_plan(plan, dry_run=False)

        self.assertEqual(result["inserted_components"], ["base_plate_1", "post_left", "post_right"])
        set_transform.assert_not_called()
        self.assertEqual(len(result["transform_reports"]), 3)
        self.assertEqual(result["transform_reports"][1]["instance_id"], "post_left")
        self.assertEqual(result["transform_reports"][2]["instance_id"], "post_right")
        self.assertNotEqual(
            result["transform_reports"][1]["requested_translation_mm"],
            result["transform_reports"][2]["requested_translation_mm"],
        )

    def test_executor_reports_structured_mate_failure(self) -> None:
        plan = build_assembly_plan("tube_with_two_end_discs", DEFAULT_PARAMETERS)
        assembly_model = FakeAssemblyModel(mate_success=False)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "tube_with_two_end_discs.SLDASM"

            def fake_save(_assembly_model, _filepath):
                output_path.write_text("assembly", encoding="utf-8")
                return {"status": "success", "filepath": str(output_path)}

            component_results = {
                "tube": ComponentBuildResult(
                    "tube", "tube", "tube", "body", "tube.SLDPRT", "tube.SLDPRT", 1, True
                ),
                "cap": ComponentBuildResult(
                    "cap", "cap", "disc", "end_cap", "cap.SLDPRT", "cap.SLDPRT", 2, True
                ),
            }

            with patch("cad_tools.assemblies.create_components_for_plan", return_value=component_results), \
                patch("cad_tools.assemblies.connect_solidworks", return_value=object()), \
                patch("cad_tools.assemblies.create_new_assembly", return_value=assembly_model), \
                patch("cad_tools.assemblies.insert_component", side_effect=lambda *_args: FakeComponent()), \
                patch("cad_tools.assemblies.set_component_transform", side_effect=_fake_transform_report), \
                patch("cad_tools.assemblies.fix_component"), \
                patch("cad_tools.assemblies.save_assembly", side_effect=fake_save):
                result = execute_assembly_plan(plan, dry_run=False)

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "partial_failure")
        self.assertGreaterEqual(len(result["constraints_failed"]), 1)
        self.assertIn("constraint_id", result["constraints_failed"][0])


class FakeComponent:
    def __init__(self, name: str = "component") -> None:
        self.name = name

    def Select4(self, *_args):
        return True


class FakeAssemblyModel:
    def __init__(self, mate_success: bool = True) -> None:
        self.mate_success = mate_success

    def AddMate5(self, *_args):
        return object() if self.mate_success else None

    def ForceRebuild3(self, *_args):
        return True


def _fake_transform_report(_component, transform):
    return {
        "applied": True,
        "requested_translation_mm": (
            transform.translation_x,
            transform.translation_y,
            transform.translation_z,
        ),
        "actual_translation_mm": (
            transform.translation_x,
            transform.translation_y,
            transform.translation_z,
        ),
        "error": None,
    }


if __name__ == "__main__":
    unittest.main()
