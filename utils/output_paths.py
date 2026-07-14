"""User-facing output path helpers for MCP SolidWorks."""

from __future__ import annotations

import os
from pathlib import Path


OUTPUT_ROOT_ENV_VAR = "MCP_SOLIDWORKS_OUTPUT_ROOT"


def get_user_output_root() -> Path:
    override = os.environ.get(OUTPUT_ROOT_ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / "Documents" / "MCP SolidWorks" / "Outputs").resolve()


def get_parts_output_dir() -> Path:
    return get_user_output_root() / "Parts"


def get_exports_output_dir() -> Path:
    return get_user_output_root() / "Exports"


def get_assemblies_output_dir() -> Path:
    return get_user_output_root() / "Assemblies"


def ensure_output_dirs() -> tuple[Path, Path, Path, Path]:
    root = get_user_output_root()
    parts = get_parts_output_dir()
    exports = get_exports_output_dir()
    assemblies = get_assemblies_output_dir()
    for directory in (root, parts, exports, assemblies):
        directory.mkdir(parents=True, exist_ok=True)
    return root, parts, exports, assemblies


def is_safe_output_path(path: str | Path) -> bool:
    root = get_user_output_root()
    try:
        resolved_path = Path(path).expanduser().resolve()
        resolved_root = root.resolve()
    except OSError:
        return False
    return resolved_path == resolved_root or resolved_root in resolved_path.parents
