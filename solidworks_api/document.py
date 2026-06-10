"""SolidWorks document helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import DEFAULT_TEMPLATE_PATH, ensure_unique_filepath


def create_new_part(sw_app: Any, template_path: str | None = None) -> Any:
    template = template_path or DEFAULT_TEMPLATE_PATH

    try:
        if template:
            template_file = Path(template)
            if not template_file.exists():
                raise RuntimeError(f"SolidWorks part template does not exist: {template}")
            model = sw_app.NewDocument(str(template_file), 0, 0, 0)
        else:
            try:
                model = sw_app.NewPart()
            except Exception:
                model = sw_app.NewDocument("", 0, 0, 0)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "Could not create a new SolidWorks part. If SolidWorks 2022 cannot "
            "create a blank part, configure a valid part template path."
        ) from exc

    if model is None:
        raise RuntimeError(
            "SolidWorks did not return a part document. Configure a valid "
            "SolidWorks 2022 part template path if blank part creation fails."
        )
    return model


def save_part(model: Any, filepath: str) -> dict[str, str]:
    target = ensure_unique_filepath(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        success = model.SaveAs(str(target))
    except Exception as exc:
        raise RuntimeError(f"Could not save SolidWorks part to {target}.") from exc

    if not success:
        raise RuntimeError(f"SolidWorks reported failure while saving part to {target}.")

    return {"status": "success", "filepath": str(target)}
