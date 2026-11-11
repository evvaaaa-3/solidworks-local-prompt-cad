"""Service layer adapting the deterministic Prompt-to-CAD pipeline for HTTP."""

from __future__ import annotations

import io
import traceback
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.solidworks_lock import solidworks_operation_lock
from parser.intent_parser import parse_prompt_with_metadata
from router.tool_router import route_intent
from schemas.intent_schema import SUPPORTED_TOOL_NAMES
from utils.output_paths import (
    ensure_output_dirs,
    get_assemblies_output_dir,
    get_exports_output_dir,
    get_parts_output_dir,
    is_safe_output_path,
)
from validator.validate_intent import validate_intent


SUPPORTED_TOOLS = SUPPORTED_TOOL_NAMES


class ApiServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _dump_model(value: Any) -> dict[str, Any]:
    return value.model_dump() if hasattr(value, "model_dump") else dict(value)


def parse_prompt(prompt: str, parser_mode: str = "rule", model_name: str | None = None) -> dict[str, Any]:
    try:
        result = parse_prompt_with_metadata(prompt, parser_mode=parser_mode, model_name=model_name)
    except ValueError as exc:
        return _parse_response(False, prompt, None, None, "invalid_parser_mode", str(exc))
    metadata = result.metadata
    if not result.success:
        return _parse_response(
            False,
            prompt,
            result.parsed_intent,
            None,
            metadata.error_code,
            metadata.error,
            metadata=metadata,
        )
    return _parse_response(
        True,
        prompt,
        result.parsed_intent,
        _dump_model(result.validated_intent),
        None,
        None,
        metadata=metadata,
    )


def _parse_response(
    success: bool,
    prompt: str,
    parsed: dict[str, Any] | None,
    validated: dict[str, Any] | None,
    code: str | None,
    error: str | None,
    *,
    metadata: Any | None = None,
) -> dict[str, Any]:
    return {
        "success": success,
        "raw_prompt": prompt,
        "normalized_prompt": getattr(metadata, "normalized_prompt", None),
        "preprocessing": getattr(metadata, "preprocessing", {}),
        "parsed_intent": parsed,
        "validated_intent": validated,
        "parser_used": getattr(metadata, "parser_used", None),
        "confidence": getattr(metadata, "confidence", None),
        "missing_fields": getattr(metadata, "missing_fields", []),
        "warnings": getattr(metadata, "warnings", []),
        "clarification_required": getattr(metadata, "clarification_required", False),
        "clarification_message": getattr(metadata, "clarification_message", None),
        "validation_status": "valid" if success else code,
        "error": error,
    }


def execute_prompt(
    prompt: str,
    mode: str,
    confirmed: bool,
    parser_mode: str = "rule",
    model_name: str | None = None,
) -> dict[str, Any]:
    if mode == "real" and not confirmed:
        raise ApiServiceError("Real SolidWorks mode requires explicit confirmation.")

    logs: list[str] = []
    parsed_result = parse_prompt_with_metadata(prompt, parser_mode=parser_mode, model_name=model_name)
    if not parsed_result.success:
        raise ApiServiceError(parsed_result.metadata.error or "Prompt parsing failed.")
    parsed = parsed_result.parsed_intent
    validated = parsed_result.validated_intent
    validated_dump = _dump_model(validated)
    logs.append(f"NLP normalized: {parsed_result.metadata.normalized_prompt}")
    logs.append(f"Prompt parsed successfully with {parsed_result.metadata.parser_used}")
    logs.append("Intent validated successfully")

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
        "normalized_prompt": parsed_result.metadata.normalized_prompt,
        "preprocessing": parsed_result.metadata.preprocessing,
        "parsed_intent": parsed, "validated_intent": validated_dump,
        "result": result, "logs": logs, "error": None,
        "parser_used": parsed_result.metadata.parser_used,
        "confidence": parsed_result.metadata.confidence,
        "missing_fields": parsed_result.metadata.missing_fields,
        "warnings": parsed_result.metadata.warnings,
        "clarification_required": parsed_result.metadata.clarification_required,
        "clarification_message": parsed_result.metadata.clarification_message,
        "validation_status": "valid",
        "execution_verification": {
            "status": result.get("status"),
            "verification_summary": result.get("verification_summary", []),
            "warnings": result.get("warnings", []),
            "errors": result.get("errors", []),
        },
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
