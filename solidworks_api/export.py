"""SolidWorks export helpers."""

from __future__ import annotations

from typing import Any

from config import ensure_unique_filepath


def export_step(model: Any, filepath: str) -> dict[str, str]:
    target = ensure_unique_filepath(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        success = model.SaveAs(str(target))
    except Exception as exc:
        raise RuntimeError(f"Could not export SolidWorks model as STEP to {target}.") from exc

    if not success:
        raise RuntimeError(f"SolidWorks reported failure while exporting STEP to {target}.")

    if not target.exists():
        raise RuntimeError(
            "The model was created in SolidWorks, but the file was not saved successfully. "
            "Please check the output folder or try saving manually."
        )

    return {"status": "success", "filepath": str(target)}
