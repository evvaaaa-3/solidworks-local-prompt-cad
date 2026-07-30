"""SolidWorks COM mate wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SW_MATE_TYPES = {
    "coincident": 0,
    "parallel": 3,
    "concentric": 1,
    "distance": 5,
    "angle": 6,
}
SW_ALIGNMENTS = {
    "aligned": 0,
    "anti_aligned": 1,
    "closest": 2,
    "opposed": 1,
}


@dataclass(frozen=True)
class MateResult:
    constraint_id: str
    constraint_type: str
    success: bool
    message: str
    solidworks_error: str | None = None


def rebuild_assembly(assembly_model: Any) -> bool:
    """Attempt to rebuild the active assembly document."""

    for method_name, args in (("ForceRebuild3", (False,)), ("EditRebuild3", ())):
        try:
            method = getattr(assembly_model, method_name)
        except Exception:
            continue
        try:
            result = method(*args)
        except Exception as exc:
            print(f"[SolidWorks] {method_name} failed: {exc}")
            continue
        return bool(result) if result is not None else True
    return False


def apply_mate(
    assembly_model: Any,
    *,
    constraint_id: str,
    constraint_type: str,
    alignment: str = "aligned",
    value_m: float = 0.0,
) -> MateResult:
    """Apply a generic mate using the current SolidWorks selection set."""

    if constraint_type not in SW_MATE_TYPES:
        return MateResult(
            constraint_id=constraint_id,
            constraint_type=constraint_type,
            success=False,
            message=f"Unsupported SolidWorks mate type: {constraint_type}",
        )
    mate_type = SW_MATE_TYPES[constraint_type]
    align = SW_ALIGNMENTS.get(alignment, 0)
    try:
        if hasattr(assembly_model, "AddMate5"):
            mate = assembly_model.AddMate5(mate_type, align, False, value_m, value_m, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, False, False, 0)
        elif hasattr(assembly_model, "AddMate3"):
            mate = assembly_model.AddMate3(mate_type, align, False, value_m, value_m, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, False, 0)
        else:
            return MateResult(
                constraint_id=constraint_id,
                constraint_type=constraint_type,
                success=False,
                message="Assembly model does not expose AddMate5/AddMate3",
            )
    except Exception as exc:
        return MateResult(
            constraint_id=constraint_id,
            constraint_type=constraint_type,
            success=False,
            message="SolidWorks mate creation raised an exception",
            solidworks_error=str(exc),
        )
    if mate is None:
        return MateResult(
            constraint_id=constraint_id,
            constraint_type=constraint_type,
            success=False,
            message="SolidWorks returned no mate object",
        )
    return MateResult(
        constraint_id=constraint_id,
        constraint_type=constraint_type,
        success=True,
        message="Mate applied",
    )
