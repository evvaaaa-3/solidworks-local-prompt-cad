from __future__ import annotations

import unittest
from unittest.mock import patch

from cad_tools.part_executor import _execute_cut
from cad_tools.part_planner import build_part_plan
from cad_tools.cad_schemas import FeatureSpec
from solidworks_api.features import SolidWorksCutExtrudeError, cut_extrude_through_all


class SolidWorksCutFeatureTests(unittest.TestCase):
    def test_preferred_feature_cut4_succeeds(self) -> None:
        model = FakeModel()

        feature = cut_extrude_through_all(model, feature_id="tube_bore_cut")

        self.assertIsNotNone(feature)
        self.assertEqual(model.feature_manager.attempted, ["FeatureCut4"])

    def test_feature_cut4_unavailable_and_cut3_succeeds(self) -> None:
        model = FakeModel(available_methods={"FeatureCut3"})

        feature = cut_extrude_through_all(model, feature_id="fallback_cut")

        self.assertIsNotNone(feature)
        self.assertEqual(model.feature_manager.attempted, ["FeatureCut3"])

    def test_com_method_raises_exception_reports_method(self) -> None:
        model = FakeModel(method_behaviour={"FeatureCut4": RuntimeError("type mismatch")})

        with self.assertRaises(SolidWorksCutExtrudeError) as raised:
            cut_extrude_through_all(model, feature_id="bad_cut")

        self.assertIn("FeatureCut4", str(raised.exception))
        self.assertIn("type mismatch", str(raised.exception))

    def test_com_method_returns_none_reports_method(self) -> None:
        model = FakeModel(method_behaviour={"FeatureCut4": None})

        with self.assertRaises(SolidWorksCutExtrudeError) as raised:
            cut_extrude_through_all(model, feature_id="none_cut")

        self.assertIn("FeatureCut4", str(raised.exception))
        self.assertIn("returned=None", str(raised.exception))

    def test_no_base_solid_exists_fails_before_cut(self) -> None:
        model = FakeModel(has_bodies=False)

        with self.assertRaises(SolidWorksCutExtrudeError) as raised:
            cut_extrude_through_all(model, feature_id="floating_cut")

        self.assertIn("base_solid_exists=False", str(raised.exception))
        self.assertEqual(model.feature_manager.attempted, [])

    def test_active_sketch_is_exited_before_cut(self) -> None:
        model = FakeModel(sketch_active=True)

        cut_extrude_through_all(model, feature_id="active_sketch_cut")

        self.assertGreaterEqual(model.sketch_manager.insert_sketch_calls, 1)

    def test_cut_sketch_selection_failure_is_not_silent(self) -> None:
        model = FakeModel(sketch=FakeSketch(select_result=False))
        feature = FeatureSpec(
            feature_id="tube_bore_cut",
            feature_type="cut_extrude",
            parameters={"profile": "center_circle", "diameter_mm": 20.0, "through_all": True},
            operation_order=10,
        )

        with patch("cad_tools.part_executor.select_front_plane"), \
            self.assertRaisesRegex(RuntimeError, "sketch selection failed"):
            _execute_cut(model, feature)

    def test_tube_part_plan_contains_boss_followed_by_cut(self) -> None:
        plan = build_part_plan(
            part_name="tube",
            component_type="tube",
            dimensions={
                "outer_diameter_mm": 50.0,
                "inner_diameter_mm": 30.0,
                "height_mm": 100.0,
            },
        )

        ordered = plan.ordered_features()
        self.assertEqual([feature.feature_id for feature in ordered], ["tube_body", "tube_bore_cut"])
        self.assertEqual([feature.feature_type for feature in ordered], ["boss_extrude", "cut_extrude"])

    def test_feature_operation_order_remains_deterministic(self) -> None:
        plan = build_part_plan(
            part_name="tube",
            component_type="tube",
            dimensions={
                "outer_diameter_mm": 50.0,
                "inner_diameter_mm": 30.0,
                "height_mm": 100.0,
            },
            features=(
                FeatureSpec(
                    feature_id="finish_chamfer",
                    feature_type="chamfer",
                    parameters={"distance_mm": 1.0},
                    operation_order=20,
                ),
            ),
        )

        self.assertEqual(
            [feature.feature_id for feature in plan.ordered_features()],
            ["tube_body", "tube_bore_cut", "finish_chamfer"],
        )


class FakeFeature:
    Name = "Cut-Extrude1"

    def GetTypeName2(self):
        return "Cut"


class FakeFeatureManager:
    def __init__(self, available_methods: set[str], behaviour: dict[str, object]) -> None:
        self.available_methods = available_methods
        self.behaviour = behaviour
        self.attempted: list[str] = []

    def __getattr__(self, name: str):
        if name not in self.available_methods:
            raise AttributeError(name)

        def method(*_args):
            self.attempted.append(name)
            behaviour = self.behaviour.get(name, FakeFeature())
            if isinstance(behaviour, Exception):
                raise behaviour
            return behaviour

        return method


class FakeSelectionManager:
    def GetSelectedObjectCount2(self, _mark):
        return 1


class FakeSketch:
    def __init__(self, select_result: bool = True) -> None:
        self.select_result = select_result

    def Select2(self, *_args):
        return self.select_result


class FakeSketchManager:
    def __init__(self, sketch: FakeSketch | None = None, active: bool = False) -> None:
        self.sketch = sketch or FakeSketch()
        self.active = active
        self.insert_sketch_calls = 0

    @property
    def ActiveSketch(self):
        return self.sketch if self.active else None

    def InsertSketch(self, *_args):
        self.insert_sketch_calls += 1
        self.active = not self.active
        return True

    def CreateCircleByRadius(self, *_args):
        return object()


class FakeModel:
    def __init__(
        self,
        *,
        available_methods: set[str] | None = None,
        method_behaviour: dict[str, object] | None = None,
        has_bodies: bool = True,
        sketch_active: bool = False,
        sketch: FakeSketch | None = None,
    ) -> None:
        self.feature_manager = FakeFeatureManager(
            available_methods or {"FeatureCut4"},
            method_behaviour or {},
        )
        self.FeatureManager = self.feature_manager
        self.SelectionManager = FakeSelectionManager()
        self.sketch_manager = FakeSketchManager(sketch=sketch, active=sketch_active)
        self.SketchManager = self.sketch_manager
        self.has_bodies = has_bodies

    def GetTitle(self):
        return "Part1"

    def GetType(self):
        return 1

    def GetBodies2(self, *_args):
        return [object()] if self.has_bodies else []

    def ForceRebuild3(self, *_args):
        return True


if __name__ == "__main__":
    unittest.main()
