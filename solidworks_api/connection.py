"""SolidWorks COM connection helpers."""

from __future__ import annotations

from typing import Any


def connect_solidworks(visible: bool = True) -> Any:
    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 is required for SolidWorks COM automation. "
            "Install dependencies with 'pip install -r requirements.txt'."
        ) from exc

    try:
        sw_app = win32com.client.Dispatch("SldWorks.Application")
        sw_app.Visible = visible
        return sw_app
    except Exception as exc:
        raise RuntimeError(
            "Could not connect to SolidWorks via COM. Confirm SolidWorks 2022 "
            "is installed, licensed, and can be started on this Windows machine."
        ) from exc


def get_active_doc(sw_app: Any) -> Any:
    try:
        model = sw_app.ActiveDoc
    except Exception as exc:
        raise RuntimeError("Could not access the active SolidWorks document.") from exc

    if model is None:
        raise RuntimeError("No active SolidWorks document is open.")
    return model
