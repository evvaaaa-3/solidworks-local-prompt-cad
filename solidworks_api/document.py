"""SolidWorks document helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import DEFAULT_TEMPLATE_PATH, ensure_unique_filepath


SW_DOC_PART = 1
SW_DEFAULT_TEMPLATE_PART = 1


def _describe_model(model: Any) -> str:
    if model is None:
        return "None"
    title = safe_get_title(model)
    return f"object ({title})"


def _get_com_value(obj: Any, name: str) -> Any:
    value = getattr(obj, name)
    if callable(value):
        return value()
    return value


def safe_get_title(model: Any) -> str:
    for attribute in ("GetTitle", "GetPathName"):
        try:
            value = _get_com_value(model, attribute)
        except Exception:
            continue
        if value:
            return str(value)
    return "<unknown title>"


def safe_get_doc_type(model: Any) -> int | None:
    for attribute in ("GetType", "GetType2"):
        try:
            value = _get_com_value(model, attribute)
        except Exception as exc:
            print(f"[SolidWorks] Could not read document type via {attribute}: {exc}")
            continue

        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            print(f"[SolidWorks] Document type from {attribute} was not numeric: {exc}")
            continue

    print("[SolidWorks] Could not validate document type; continuing with ActiveDoc.")
    return None


def _get_default_part_template(sw_app: Any) -> str | None:
    try:
        template = sw_app.GetUserPreferenceStringValue(SW_DEFAULT_TEMPLATE_PART)
    except Exception as exc:
        print(f"[SolidWorks] Could not read default part template preference: {exc}")
        return None

    if not template:
        print("[SolidWorks] Default part template preference is empty.")
        return None

    template_file = Path(template)
    if not template_file.exists():
        print(f"[SolidWorks] Default part template path missing: {template}")
        return None

    return str(template_file)


def _try_new_document(sw_app: Any, template: str) -> Any:
    print(f"[SolidWorks] Attempting template path: {template}")
    try:
        model = sw_app.NewDocument(template, 0, 0, 0)
    except Exception as exc:
        print(f"[SolidWorks] NewDocument failed for template path: {exc}")
        return None

    print(f"[SolidWorks] NewDocument returned {_describe_model(model)}.")
    return model


def _try_new_part(sw_app: Any) -> Any:
    print("[SolidWorks] Attempting default NewPart creation.")
    try:
        model = sw_app.NewPart()
    except Exception as exc:
        print(f"[SolidWorks] NewPart failed: {exc}")
        return None

    print(f"[SolidWorks] NewPart returned {_describe_model(model)}.")
    return model


def _active_doc(sw_app: Any) -> Any:
    print("[SolidWorks] Fallback to ActiveDoc.")
    try:
        model = sw_app.ActiveDoc
    except Exception as exc:
        raise RuntimeError("Could not access SolidWorks ActiveDoc after part creation.") from exc

    if model is None:
        raise RuntimeError(
            "SolidWorks did not expose an ActiveDoc after part creation. "
            "Check the configured SolidWorks 2022 part template."
        )

    print(f"[SolidWorks] ActiveDoc object type: {type(model)}")
    title = safe_get_title(model)
    print(f"[SolidWorks] ActiveDoc title/name: {title}")
    return model


def _validate_part_document(model: Any) -> None:
    doc_type = safe_get_doc_type(model)
    if doc_type is None:
        return

    if doc_type != SW_DOC_PART:
        print(
            "[SolidWorks] ActiveDoc document type is not a part "
            f"({doc_type}); continuing with ActiveDoc."
        )


def create_new_part(sw_app: Any, template_path: str | None = None) -> Any:
    template = template_path or DEFAULT_TEMPLATE_PATH
    model = None

    if template:
        template_file = Path(template)
        if template_file.exists():
            model = _try_new_document(sw_app, str(template_file))
        else:
            print(f"[SolidWorks] Template path missing: {template}")
    else:
        print("[SolidWorks] Template path missing; no explicit template configured.")

    if model is None:
        default_template = _get_default_part_template(sw_app)
        if default_template:
            model = _try_new_document(sw_app, default_template)

    if model is None:
        model = _try_new_part(sw_app)

    if model is None:
        print("[SolidWorks] Part creation call returned None; checking ActiveDoc.")

    active_model = _active_doc(sw_app)
    _validate_part_document(active_model)
    return active_model


def save_part(model: Any, filepath: str) -> dict[str, str]:
    target = ensure_unique_filepath(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        success = model.SaveAs(str(target))
    except Exception as exc:
        raise RuntimeError(f"Could not save SolidWorks part to {target}.") from exc

    if not success:
        raise RuntimeError(f"SolidWorks reported failure while saving part to {target}.")

    if not target.exists():
        raise RuntimeError(
            "The model was created in SolidWorks, but the file was not saved successfully. "
            "Please check the output folder or try saving manually."
        )

    return {"status": "success", "filepath": str(target)}
