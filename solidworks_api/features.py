"""SolidWorks feature helpers."""

from __future__ import annotations

from typing import Any


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
