"""Deterministic dry-run CAD primitive functions for Stage 1."""

from __future__ import annotations

from typing import Any


def create_cube(side_mm: float) -> dict[str, Any]:
    result = {
        "status": "dry_run_success",
        "tool": "create_cube",
        "parameters": {"side_mm": side_mm},
    }
    print(f"[DRY CAD TOOL] Would create cube with side {side_mm:g} mm.")
    return result


def create_block(length_mm: float, width_mm: float, height_mm: float) -> dict[str, Any]:
    result = {
        "status": "dry_run_success",
        "tool": "create_block",
        "parameters": {
            "length_mm": length_mm,
            "width_mm": width_mm,
            "height_mm": height_mm,
        },
    }
    print(
        f"[DRY CAD TOOL] Would create block {length_mm:g} mm x "
        f"{width_mm:g} mm x {height_mm:g} mm."
    )
    return result


def create_cylinder(diameter_mm: float, height_mm: float) -> dict[str, Any]:
    result = {
        "status": "dry_run_success",
        "tool": "create_cylinder",
        "parameters": {
            "diameter_mm": diameter_mm,
            "height_mm": height_mm,
        },
    }
    print(
        f"[DRY CAD TOOL] Would create cylinder with diameter {diameter_mm:g} mm "
        f"and height {height_mm:g} mm."
    )
    return result


dry_run_create_cube = create_cube
dry_run_create_block = create_block
dry_run_create_cylinder = create_cylinder
