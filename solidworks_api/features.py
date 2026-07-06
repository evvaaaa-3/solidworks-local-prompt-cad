"""SolidWorks feature helpers."""

from __future__ import annotations

from typing import Any
import math


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
    try:
        feature = model.FeatureManager.FeatureCut4(
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
        )
    except Exception as exc:
        raise RuntimeError("Could not create SolidWorks cut extrusion.") from exc

    if feature is None:
        raise RuntimeError("SolidWorks failed to create cut extrusion.")
    return feature


def cut_extrude_through_all(model: Any) -> Any:
    try:
        feature = model.FeatureManager.FeatureCut4(
            True,
            False,
            False,
            1,
            0,
            0.0,
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
        )
    except Exception as exc:
        raise RuntimeError("Could not create SolidWorks through-all cut extrusion.") from exc

    if feature is None:
        raise RuntimeError("SolidWorks failed to create through-all cut extrusion.")
    return feature


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
