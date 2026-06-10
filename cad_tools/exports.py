"""Deterministic export functions with Stage 1 dry-run support."""

from __future__ import annotations

from typing import Any

from config import EXPORTS_DIR, sanitize_filename
from solidworks_api.connection import connect_solidworks, get_active_doc
from solidworks_api.export import export_step as solidworks_export_step


def export_step(filename: str, dry_run: bool = True) -> dict[str, Any]:
    safe_filename = sanitize_filename(filename)

    if not dry_run:
        sw_app = connect_solidworks(visible=True)
        model = get_active_doc(sw_app)
        export_result = solidworks_export_step(model, str(EXPORTS_DIR / safe_filename))
        return {
            "status": "success",
            "tool": "export_step",
            "parameters": {"filename": safe_filename},
            "filepath": export_result["filepath"],
        }

    result = {
        "status": "dry_run_success",
        "tool": "export_step",
        "parameters": {"filename": safe_filename},
    }
    print(f"[DRY CAD TOOL] Would export current model as {safe_filename}.")
    return result


dry_run_export_step = export_step
