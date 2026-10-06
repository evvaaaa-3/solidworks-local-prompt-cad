"""SolidWorks COM connection helpers."""

from __future__ import annotations

import time
from typing import Any


def _wait_until_responsive(sw_app: Any, timeout_seconds: float, interval_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            # Accessing a light property is enough to let a freshly launched
            # SolidWorks COM server finish startup before document calls begin.
            _ = sw_app.Visible
            return
        except Exception as exc:
            last_error = exc
            time.sleep(interval_seconds)
    if last_error is not None:
        raise RuntimeError("SolidWorks COM server did not become responsive after launch.") from last_error


def connect_solidworks(
    visible: bool = True,
    startup_timeout_seconds: float = 20.0,
    retry_interval_seconds: float = 0.5,
) -> Any:
    """Connect to SolidWorks, launching it when no running COM server is attached."""

    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 is required for SolidWorks COM automation. "
            "Install dependencies with 'pip install -r requirements.txt'."
        ) from exc

    attached = False
    try:
        sw_app = win32com.client.GetActiveObject("SldWorks.Application")
        attached = True
    except Exception:
        try:
            sw_app = win32com.client.Dispatch("SldWorks.Application")
        except Exception as exc:
            raise RuntimeError(
                "Could not connect to SolidWorks via COM. Confirm SolidWorks 2022 "
                "is installed, licensed, and can be started on this Windows machine."
            ) from exc

    try:
        sw_app.Visible = visible
    except Exception as exc:
        raise RuntimeError(
            "Connected to SolidWorks COM, but could not set the application visibility."
        ) from exc

    if not attached:
        _wait_until_responsive(sw_app, startup_timeout_seconds, retry_interval_seconds)
    return sw_app


def get_active_doc(sw_app: Any) -> Any:
    try:
        model = sw_app.ActiveDoc
    except Exception as exc:
        raise RuntimeError("Could not access the active SolidWorks document.") from exc

    if model is None:
        raise RuntimeError("No active SolidWorks document is open.")
    return model
