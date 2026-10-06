"""SolidWorks feature helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math

from solidworks_api.document import safe_get_doc_type, safe_get_title


SW_END_COND_BLIND = 0
SW_END_COND_THROUGH_ALL = 1


@dataclass(frozen=True)
class CutExtrudeDiagnostics:
    """Actionable context captured around a SolidWorks cut extrusion attempt."""

    document_name: str
    document_type: int | None
    feature_id: str
    feature_type: str
    attempted_method: str
    selected_object_count: int
    sketch_mode_active: bool
    base_solid_exists: bool
    returned_value: str
    original_error: str | None = None

    def message(self) -> str:
        return (
            "SolidWorks cut extrusion failed "
            f"(document={self.document_name}, doc_type={self.document_type}, "
            f"feature_id={self.feature_id}, feature_type={self.feature_type}, "
            f"method={self.attempted_method}, selected_objects={self.selected_object_count}, "
            f"sketch_mode_active={self.sketch_mode_active}, base_solid_exists={self.base_solid_exists}, "
            f"returned={self.returned_value}, com_error={self.original_error or '<none>'})"
        )


class SolidWorksCutExtrudeError(RuntimeError):
    """Raised when a cut extrusion fails with structured diagnostics."""

    def __init__(self, diagnostics: CutExtrudeDiagnostics) -> None:
        self.diagnostics = diagnostics
        super().__init__(diagnostics.message())


def extrude_boss(model: Any, depth_m: float) -> Any:
    try:
        feature = model.FeatureManager.FeatureExtrusion2(
            True,
            False,
            False,
            0,
            0,
            depth_m,
            0.0,
            False,
            False,
            False,
            False,
            0.0,
            0.0,
            False,
            False,
            False,
            False,
            True,
            True,
            True,
            0,
            0,
            False,
        )
    except Exception as exc:
        raise RuntimeError("Could not create SolidWorks boss extrusion.") from exc

    if feature is None:
        raise RuntimeError("SolidWorks failed to create boss extrusion.")
    return feature


def cut_extrude_depth(model: Any, depth_m: float) -> Any:
    return cut_extrude(
        model,
        feature_id="cut_extrude",
        feature_type="cut_extrude",
        through_all=False,
        depth_m=depth_m,
    )


def cut_extrude_through_all(
    model: Any,
    *,
    feature_id: str = "cut_extrude",
    feature_type: str = "cut_extrude",
    reverse: bool = False,
    both_directions: bool = True,
) -> Any:
    return cut_extrude(
        model,
        feature_id=feature_id,
        feature_type=feature_type,
        through_all=True,
        reverse=reverse,
        both_directions=both_directions,
    )


def cut_extrude(
    model: Any,
    *,
    feature_id: str,
    feature_type: str,
    through_all: bool,
    depth_m: float = 0.0,
    reverse: bool = False,
    both_directions: bool = False,
) -> Any:
    """Create a SolidWorks cut extrusion with FeatureCut fallback support."""

    document_name = safe_get_title(model)
    document_type = safe_get_doc_type(model)
    print(f"[SolidWorks] Cut feature {feature_id}: active document {document_name}, type {document_type}")
    _exit_sketch_if_active(model, feature_id)
    selected_count = _selected_object_count(model)
    base_solid_exists = _base_solid_exists(model)
    if not base_solid_exists:
        raise SolidWorksCutExtrudeError(
            _diagnostics(
                model,
                feature_id,
                feature_type,
                "<preflight>",
                selected_count,
                base_solid_exists,
                "not attempted",
                "No base solid body exists before cut extrusion.",
            )
        )
    _rebuild_or_raise(model, feature_id, feature_type)

    last_error: SolidWorksCutExtrudeError | None = None
    for method_name, args in _cut_method_attempts(
        through_all=through_all,
        depth_m=depth_m,
        reverse=reverse,
        both_directions=both_directions,
    ):
        feature_manager = getattr(model, "FeatureManager", None)
        method = getattr(feature_manager, method_name, None)
        if method is None:
            print(f"[SolidWorks] FeatureCut method unavailable: {method_name}")
            continue
        print(f"[SolidWorks] Attempting {method_name} for cut feature {feature_id}")
        try:
            feature = method(*args)
        except Exception as exc:
            last_error = SolidWorksCutExtrudeError(
                _diagnostics(
                    model,
                    feature_id,
                    feature_type,
                    method_name,
                    _selected_object_count(model),
                    base_solid_exists,
                    "exception",
                    str(exc),
                )
            )
            print(f"[SolidWorks] {method_name} raised: {exc}")
            continue
        print(f"[SolidWorks] {method_name} returned feature object: {feature is not None}")
        if feature is None:
            last_error = SolidWorksCutExtrudeError(
                _diagnostics(
                    model,
                    feature_id,
                    feature_type,
                    method_name,
                    _selected_object_count(model),
                    base_solid_exists,
                    "None",
                    None,
                )
            )
            continue
        _log_feature_identity(feature)
        _rebuild_or_raise(model, feature_id, feature_type)
        return feature

    if last_error is not None:
        raise last_error
    raise SolidWorksCutExtrudeError(
        _diagnostics(
            model,
            feature_id,
            feature_type,
            "<none>",
            selected_count,
            base_solid_exists,
            "not attempted",
            "No supported FeatureCut method is available.",
        )
    )


def _cut_method_attempts(
    *,
    through_all: bool,
    depth_m: float,
    reverse: bool,
    both_directions: bool,
) -> tuple[tuple[str, tuple[Any, ...]], ...]:
    end_condition = SW_END_COND_THROUGH_ALL if through_all else SW_END_COND_BLIND
    direction2 = SW_END_COND_THROUGH_ALL if both_directions and through_all else SW_END_COND_BLIND
    depth1 = 0.0 if through_all else depth_m
    depth2 = 0.0 if through_all else depth_m
    return (
        (
            "FeatureCut4",
            (
                True,
                False,
                bool(reverse),
                end_condition,
                direction2,
                float(depth1),
                float(depth2),
                False,
                False,
                False,
                False,
                0.0,
                0.0,
                False,
                False,
                False,
                False,
                False,
                True,
                True,
                True,
                True,
                False,
                0,
                0,
                False,
                False,
            ),
        ),
        (
            "FeatureCut3",
            (
                True,
                False,
                bool(reverse),
                end_condition,
                direction2,
                float(depth1),
                float(depth2),
                False,
                False,
                False,
                False,
                0.0,
                0.0,
                False,
                False,
                False,
                False,
                False,
                True,
                True,
                True,
                False,
                False,
            ),
        ),
        (
            "FeatureCut2",
            (
                True,
                False,
                bool(reverse),
                end_condition,
                direction2,
                float(depth1),
                float(depth2),
                False,
                False,
                False,
                False,
                0.0,
                0.0,
                False,
                False,
                False,
                False,
                False,
                True,
                True,
                True,
            ),
        ),
    )


def _diagnostics(
    model: Any,
    feature_id: str,
    feature_type: str,
    attempted_method: str,
    selected_object_count: int,
    base_solid_exists: bool,
    returned_value: str,
    original_error: str | None,
) -> CutExtrudeDiagnostics:
    return CutExtrudeDiagnostics(
        document_name=safe_get_title(model),
        document_type=safe_get_doc_type(model),
        feature_id=feature_id,
        feature_type=feature_type,
        attempted_method=attempted_method,
        selected_object_count=selected_object_count,
        sketch_mode_active=_sketch_mode_active(model),
        base_solid_exists=base_solid_exists,
        returned_value=returned_value,
        original_error=original_error,
    )


def _selected_object_count(model: Any) -> int:
    selection_manager = getattr(model, "SelectionManager", None)
    if selection_manager is None:
        print("[SolidWorks] SelectionManager unavailable before cut.")
        return 0
    for method_name, args in (("GetSelectedObjectCount2", (-1,)), ("GetSelectedObjectCount", ())):
        method = getattr(selection_manager, method_name, None)
        if method is None:
            continue
        try:
            count = int(method(*args))
        except Exception as exc:
            print(f"[SolidWorks] Could not read selected object count via {method_name}: {exc}")
            continue
        print(f"[SolidWorks] Selected object count before cut: {count}")
        return count
    return 0


def _sketch_mode_active(model: Any) -> bool:
    sketch_manager = getattr(model, "SketchManager", None)
    if sketch_manager is None:
        return False
    for name in ("ActiveSketch", "GetActiveSketch2"):
        try:
            value = getattr(sketch_manager, name)
            if callable(value):
                value = value()
        except Exception:
            continue
        if value is not None:
            return True
    return False


def _exit_sketch_if_active(model: Any, feature_id: str) -> None:
    if not _sketch_mode_active(model):
        print(f"[SolidWorks] Cut feature {feature_id}: sketch mode already exited.")
        return
    try:
        model.SketchManager.InsertSketch(True)
    except Exception as exc:
        raise SolidWorksCutExtrudeError(
            _diagnostics(
                model,
                feature_id,
                "cut_extrude",
                "<exit-sketch>",
                _selected_object_count(model),
                _base_solid_exists(model),
                "not attempted",
                f"Could not exit active sketch before cut: {exc}",
            )
        ) from exc
    print(f"[SolidWorks] Cut feature {feature_id}: active sketch exited before cut.")


def _base_solid_exists(model: Any) -> bool:
    for method_name, args in (("GetBodies2", (0, False)), ("GetBodies", (0,))):
        method = getattr(model, method_name, None)
        if method is None:
            continue
        try:
            bodies = method(*args)
        except Exception as exc:
            print(f"[SolidWorks] Could not inspect solid bodies via {method_name}: {exc}")
            continue
        exists = bool(bodies)
        print(f"[SolidWorks] Base solid exists before cut: {exists}")
        return exists
    try:
        feature = model.FirstFeature()
    except Exception:
        print("[SolidWorks] Could not inspect feature tree for base solid; assuming present.")
        return True
    exists = feature is not None
    print(f"[SolidWorks] Feature tree exists before cut: {exists}")
    return exists


def _rebuild_or_raise(model: Any, feature_id: str, feature_type: str) -> None:
    for method_name, args in (("ForceRebuild3", (False,)), ("EditRebuild3", ())):
        method = getattr(model, method_name, None)
        if method is None:
            continue
        try:
            result = method(*args)
        except Exception as exc:
            raise SolidWorksCutExtrudeError(
                _diagnostics(
                    model,
                    feature_id,
                    feature_type,
                    f"<{method_name}>",
                    _selected_object_count(model),
                    _base_solid_exists(model),
                    "not attempted",
                    str(exc),
                )
            ) from exc
        print(f"[SolidWorks] {method_name} before/after cut returned: {result}")
        return
    print("[SolidWorks] No rebuild method exposed before/after cut.")


def _log_feature_identity(feature: Any) -> None:
    name = "<unknown>"
    feature_type = "<unknown>"
    for attr in ("Name", "GetNameForSelection"):
        try:
            value = getattr(feature, attr)
            name = str(value() if callable(value) else value)
            break
        except Exception:
            continue
    for attr in ("GetTypeName2", "GetTypeName"):
        try:
            value = getattr(feature, attr)
            feature_type = str(value() if callable(value) else value)
            break
        except Exception:
            continue
    print(f"[SolidWorks] Cut feature created: name={name}, type={feature_type}")


def revolve_boss(model: Any, angle_degrees: float = 360.0) -> Any:
    angle_radians = math.radians(angle_degrees)
    print(f"[SolidWorks] Creating boss revolve at {angle_degrees:g} degrees.")

    try:
        feature = model.FeatureManager.FeatureRevolve2(
            True,
            True,
            False,
            False,
            False,
            False,
            0,
            0,
            angle_radians,
            0.0,
            False,
            False,
            0.0,
            0.0,
            0,
            0.0,
            0.0,
            True,
            True,
            True,
        )
    except Exception as first_exc:
        print(f"[SolidWorks] FeatureRevolve2 failed: {first_exc}")
        try:
            feature = model.FeatureManager.FeatureRevolve(
                angle_radians,
                False,
                False,
                False,
                False,
                False,
            )
        except Exception as second_exc:
            raise RuntimeError("Could not create SolidWorks boss revolve.") from second_exc

    print(f"[SolidWorks] Boss revolve feature result: {feature}")
    if feature is None:
        raise RuntimeError("SolidWorks failed to create boss revolve.")
    return feature


def fillet(model: Any, radius_m: float) -> Any:
    """Create a generic constant-radius fillet from the current selection."""

    try:
        feature = model.FeatureManager.FeatureFillet3(
            195,
            radius_m,
            0.0,
            0,
            0,
            0,
            0,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
    except Exception as exc:
        raise RuntimeError("Could not create SolidWorks fillet feature.") from exc
    if feature is None:
        raise RuntimeError("SolidWorks failed to create fillet feature.")
    return feature


def chamfer(model: Any, distance_m: float) -> Any:
    """Create a generic equal-distance chamfer from the current selection."""

    try:
        feature = model.FeatureManager.InsertFeatureChamfer(4, 1, distance_m, 0.0, 0.0, 0.0, 0.0, 0.0)
    except Exception as exc:
        raise RuntimeError("Could not create SolidWorks chamfer feature.") from exc
    if feature is None:
        raise RuntimeError("SolidWorks failed to create chamfer feature.")
    return feature


def shell(model: Any, thickness_m: float) -> Any:
    """Create a generic shell feature from the current selection."""

    try:
        feature = model.FeatureManager.InsertFeatureShell(thickness_m, False)
    except Exception as exc:
        raise RuntimeError("Could not create SolidWorks shell feature.") from exc
    if feature is None:
        raise RuntimeError("SolidWorks failed to create shell feature.")
    return feature
