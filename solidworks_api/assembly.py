"""SolidWorks assembly COM helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import ensure_unique_filepath
from solidworks_api.document import safe_get_doc_type, safe_get_title


SW_DOC_ASSEMBLY = 2
SW_DEFAULT_TEMPLATE_ASSEMBLY = 2


def _get_com_value(obj: Any, name: str) -> Any:
    value = getattr(obj, name)
    if callable(value):
        return value()
    return value


def _active_doc(sw_app: Any) -> Any:
    try:
        model = sw_app.ActiveDoc
    except Exception as exc:
        raise RuntimeError("Could not access SolidWorks ActiveDoc after assembly creation.") from exc

    if model is None:
        raise RuntimeError("SolidWorks did not expose an ActiveDoc after assembly creation.")

    print(f"[SolidWorks] Active assembly document: {safe_get_title(model)}")
    return model


def _get_default_assembly_template(sw_app: Any) -> str | None:
    try:
        template = sw_app.GetUserPreferenceStringValue(SW_DEFAULT_TEMPLATE_ASSEMBLY)
    except Exception as exc:
        print(f"[SolidWorks] Could not read default assembly template preference: {exc}")
        return None

    if not template:
        print("[SolidWorks] Default assembly template preference is empty.")
        return None

    template_file = Path(template)
    if not template_file.exists():
        print(f"[SolidWorks] Default assembly template path missing: {template}")
        return None

    return str(template_file)


def _try_new_document(sw_app: Any, template: str) -> Any:
    print(f"[SolidWorks] Attempting assembly template path: {template}")
    try:
        model = sw_app.NewDocument(template, 0, 0, 0)
    except Exception as exc:
        print(f"[SolidWorks] NewDocument failed for assembly template: {exc}")
        return None
    print(f"[SolidWorks] Assembly NewDocument returned {model}.")
    return model


def _try_new_assembly(sw_app: Any) -> Any:
    print("[SolidWorks] Attempting default NewAssembly creation.")
    try:
        model = sw_app.NewAssembly()
    except Exception as exc:
        print(f"[SolidWorks] NewAssembly failed: {exc}")
        return None
    print(f"[SolidWorks] NewAssembly returned {model}.")
    return model


def create_new_assembly(sw_app: Any, template_path: str | None = None) -> Any:
    model = None
    if template_path:
        template_file = Path(template_path)
        if template_file.exists():
            model = _try_new_document(sw_app, str(template_file))
        else:
            print(f"[SolidWorks] Assembly template path missing: {template_path}")
    else:
        print("[SolidWorks] Assembly template path missing; no explicit template configured.")

    if model is None:
        default_template = _get_default_assembly_template(sw_app)
        if default_template:
            model = _try_new_document(sw_app, default_template)

    if model is None:
        model = _try_new_assembly(sw_app)

    if model is None:
        print("[SolidWorks] Assembly creation call returned None; checking ActiveDoc.")

    active_model = _active_doc(sw_app)
    doc_type = safe_get_doc_type(active_model)
    if doc_type is not None and doc_type != SW_DOC_ASSEMBLY:
        print(
            "[SolidWorks] ActiveDoc document type is not an assembly "
            f"({doc_type}); continuing with ActiveDoc."
        )
    return active_model


def insert_component(assembly_model: Any, part_filepath: str, x_m: float, y_m: float, z_m: float) -> Any:
    path = str(Path(part_filepath).resolve())
    print(f"[SolidWorks] Inserting component: {path} at ({x_m}, {y_m}, {z_m})")

    for method_name, args in (
        ("AddComponent5", (path, 0, "", False, "", x_m, y_m, z_m)),
        ("AddComponent4", (path, "", x_m, y_m, z_m)),
        ("AddComponent", (path, x_m, y_m, z_m)),
    ):
        try:
            method = getattr(assembly_model, method_name)
        except Exception:
            continue
        try:
            component = method(*args)
        except Exception as exc:
            print(f"[SolidWorks] {method_name} failed: {exc}")
            continue
        if component is not None:
            return component

    raise RuntimeError(f"Could not insert component into assembly: {path}")


def set_component_position(component: Any, x_m: float, y_m: float, z_m: float) -> None:
    try:
        transform = component.Transform2
        data = list(_get_com_value(transform, "ArrayData"))
        if len(data) >= 12:
            data[9] = x_m
            data[10] = y_m
            data[11] = z_m
            transform.ArrayData = data
            component.Transform2 = transform
            print(f"[SolidWorks] Component transform set to ({x_m}, {y_m}, {z_m}).")
    except Exception as exc:
        print(f"[SolidWorks] Component transform update skipped: {exc}")


def fix_component(assembly_model: Any, component: Any) -> None:
    try:
        select_result = component.Select4(False, None, False)
        print(f"[SolidWorks] Component select for fix: {select_result}")
        assembly_model.FixComponent()
    except Exception as exc:
        print(f"[SolidWorks] Component fix skipped: {exc}")


def save_assembly(assembly_model: Any, filepath: str) -> dict[str, str]:
    target = ensure_unique_filepath(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        success = assembly_model.SaveAs(str(target))
    except Exception as exc:
        raise RuntimeError(f"Could not save SolidWorks assembly to {target}.") from exc

    if not success:
        raise RuntimeError(f"SolidWorks reported failure while saving assembly to {target}.")

    if not target.exists():
        raise RuntimeError(
            "The assembly was created in SolidWorks, but the file was not saved successfully. "
            "Please check the output folder or try saving manually."
        )

    return {"status": "success", "filepath": str(target)}
