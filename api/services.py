"""Service layer adapting the deterministic Prompt-to-CAD pipeline for HTTP."""

from __future__ import annotations

import io
import traceback
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.solidworks_lock import solidworks_operation_lock
from parser.rule_parser import parse_prompt_rule_based
from router.tool_router import route_intent
from utils.output_paths import (
    ensure_output_dirs,
    get_assemblies_output_dir,
    get_exports_output_dir,
    get_parts_output_dir,
    is_safe_output_path,
)
from validator.validate_intent import validate_intent


SUPPORTED_TOOLS = [
    "create_cube", "create_block", "create_cylinder", "create_disc",
    "create_plate", "create_tube", "create_plate_with_hole", "create_cone",
    "create_sphere", "create_torus", "create_assembly", "export_step",
]


class ApiServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _dump_model(value: Any) -> dict[str, Any]:
    return value.model_dump() if hasattr(value, "model_dump") else dict(value)


def parse_prompt(prompt: str) -> dict[str, Any]:
    parsed = None
    try:
        parsed = parse_prompt_rule_based(prompt)
        validated = validate_intent(parsed)
    except ValueError as exc:
        return {
            "success": False, "raw_prompt": prompt, "parsed_intent": parsed,
            "validated_intent": None, "error": str(exc),
        }
    return {
        "success": True, "raw_prompt": prompt, "parsed_intent": parsed,
        "validated_intent": _dump_model(validated), "error": None,
    }


def execute_prompt(prompt: str, mode: str, confirmed: bool) -> dict[str, Any]:
    if mode == "real" and not confirmed:
        raise ApiServiceError("Real SolidWorks mode requires explicit confirmation.")

    logs: list[str] = []
    try:
        parsed = parse_prompt_rule_based(prompt)
        logs.append("Prompt parsed successfully")
        validated = validate_intent(parsed)
        validated_dump = _dump_model(validated)
        logs.append("Intent validated successfully")
    except ValueError as exc:
        raise ApiServiceError(str(exc)) from exc

    lock_acquired = False
    output = io.StringIO()
    try:
        if mode == "real":
            lock_acquired = solidworks_operation_lock.acquire(blocking=False)
            if not lock_acquired:
                raise ApiServiceError(
                    "Another real SolidWorks operation is already running. Try again shortly.",
                    status_code=409,
                )
            logs.append("Exclusive SolidWorks operation lock acquired")

        with redirect_stdout(output):
            result = route_intent(validated, dry_run=mode == "dry_run")
        logs.extend(line for line in output.getvalue().splitlines() if line)
        logs.append("Dry-run completed" if mode == "dry_run" else "SolidWorks operation completed")
    except ApiServiceError:
        raise
    except RuntimeError as exc:
        traceback.print_exc()
        raise ApiServiceError(f"SolidWorks operation failed: {exc}", 503) from exc
    except Exception as exc:
        traceback.print_exc()
        raise ApiServiceError(f"Unexpected execution error: {exc}", 500) from exc
    finally:
        if lock_acquired:
            solidworks_operation_lock.release()

    return {
        "success": True, "mode": mode, "raw_prompt": prompt,
        "parsed_intent": parsed, "validated_intent": validated_dump,
        "result": result, "logs": logs, "error": None,
    }


def list_outputs() -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    ensure_output_dirs()
    for category, directory in (
        ("parts", get_parts_output_dir()),
        ("exports", get_exports_output_dir()),
        ("assemblies", get_assemblies_output_dir()),
    ):
        for path in directory.iterdir():
            if not path.is_file() or path.name == ".gitkeep":
                continue
            stat = path.stat()
            files.append({
                "filename": path.name,
                "file_type": path.suffix.lower().lstrip(".") or "file",
                "category": category,
                "relative_path": f"outputs/{category}/{path.name}",
                "size_bytes": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            })
    return sorted(files, key=lambda item: item["modified_time"], reverse=True)


def resolve_output_file(category: str, filename: str) -> Path:
    ensure_output_dirs()
    directories = {
        "parts": get_parts_output_dir(),
        "exports": get_exports_output_dir(),
        "assemblies": get_assemblies_output_dir(),
    }
    if category not in directories:
        raise ApiServiceError("Unknown output category.", 404)
    if not filename or Path(filename).name != filename or filename in {".", ".."}:
        raise ApiServiceError("Invalid output filename.", 400)
    root = directories[category].resolve()
    candidate = (root / filename).resolve()
    if candidate.parent != root or not is_safe_output_path(candidate):
        raise ApiServiceError("Output path is outside the allowed folder.", 403)
    if not candidate.is_file():
        raise ApiServiceError("Output file not found.", 404)
    return candidate
