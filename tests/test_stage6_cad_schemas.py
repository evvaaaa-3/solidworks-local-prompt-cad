from __future__ import annotations

import math
import unittest

from pydantic import ValidationError

from cad_tools.cad_schemas import ConstraintSpec, FeatureSpec, PartPlan, ReferenceSpec, TransformSpec
from cad_tools.references import coerce_reference, validate_reference_selector
from cad_tools.transforms import (
    axis_rotation_transform,
    combined_transform,
    solidworks_transform_array,
    transform_rotation_rad,
    transform_translation_m,
)
from cad_tools.verification import build_assembly_execution_result


class Stage6SchemaTests(unittest.TestCase):
    def test_feature_spec_validation(self) -> None:
        feature = FeatureSpec(
            feature_id="main_boss",
            feature_type="boss_extrude",
            parameters={"depth_mm": 10.0},
            operation_order=1,
        )

        self.assertEqual(feature.feature_type, "boss_extrude")

    def test_unsupported_feature_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            FeatureSpec(
                feature_id="bad",
                feature_type="loft",
                parameters={},
                operation_order=1,
            )

    def test_part_plan_orders_features(self) -> None:
        base = FeatureSpec(
            feature_id="base",
            feature_type="boss_extrude",
            parameters={"depth_mm": 5.0},
            operation_order=0,
        )
        late = FeatureSpec(
            feature_id="late",
            feature_type="fillet",
            parameters={"radius_mm": 1.0},
            operation_order=20,
        )
        early = FeatureSpec(
            feature_id="early",
            feature_type="hole",
            parameters={"diameter_mm": 4.0},
            operation_order=10,
        )
        plan = PartPlan(
            part_name="plate",
            base_feature=base,
            features=[late, early],
            output_filename="plate.SLDPRT",
        )

        self.assertEqual([feature.feature_id for feature in plan.ordered_features()], ["base", "early", "late"])

    def test_transform_validation_and_conversion(self) -> None:
        transform = combined_transform((10.0, 20.0, 30.0), (90.0, 0.0, 0.0))

        self.assertEqual(transform_translation_m(transform), (0.01, 0.02, 0.03))
        self.assertAlmostEqual(transform_rotation_rad(transform)[0], math.pi / 2.0)
        self.assertEqual(solidworks_transform_array(transform)[9:12], [0.01, 0.02, 0.03])

    def test_axis_rotation_validation(self) -> None:
        self.assertEqual(axis_rotation_transform("z", 45.0).rotation_z, 45.0)
        with self.assertRaises(ValueError):
            axis_rotation_transform("q", 45.0)
        with self.assertRaises(ValidationError):
            TransformSpec(rotation_x=361.0)

    def test_constraint_spec_validation(self) -> None:
        reference = ReferenceSpec(entity_type="planar_face", selection_rule="maximum_z")
        constraint = ConstraintSpec(
            constraint_id="faces_coincident",
            constraint_type="coincident",
            component_a="a",
            reference_a=reference,
            component_b="b",
            reference_b=reference,
        )

        self.assertEqual(constraint.constraint_type, "coincident")

    def test_unsupported_constraint_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ConstraintSpec(
                constraint_id="bad",
                constraint_type="gear",
                component_a="a",
            )

    def test_missing_feature_reference_rejected(self) -> None:
        selector = ReferenceSpec(entity_type="feature_edge", feature_id="missing")
        with self.assertRaisesRegex(ValueError, "unknown feature_id"):
            validate_reference_selector(selector, {"base"})

    def test_legacy_reference_coercion(self) -> None:
        self.assertEqual(coerce_reference("top_face").selection_rule, "maximum_z")

    def test_verification_result_construction(self) -> None:
        result = build_assembly_execution_result(
            assembly_path=None,
            expected_component_count=2,
            inserted_components=["one"],
            planned_constraint_ids=["mate"],
            applied_constraint_ids=[],
            failed_constraints=[],
            component_filepaths={"part": "<pending:part>"},
            rebuild_attempted=False,
            save_checked=False,
        )

        self.assertFalse(result.success)
        self.assertIn("failed", result.status)
        self.assertGreaterEqual(len(result.errors), 3)


if __name__ == "__main__":
    unittest.main()
