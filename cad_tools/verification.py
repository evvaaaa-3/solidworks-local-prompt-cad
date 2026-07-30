"""Assembly execution verification independent of SolidWorks COM."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cad_tools.cad_schemas import AssemblyExecutionResult, ConstraintExecutionError


def build_assembly_execution_result(
    *,
    assembly_path: Path | None,
    expected_component_count: int,
    inserted_components: list[str],
    planned_constraint_ids: list[str],
    applied_constraint_ids: list[str],
    failed_constraints: list[ConstraintExecutionError],
    component_filepaths: dict[str, str],
    rebuild_attempted: bool,
    save_checked: bool,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> AssemblyExecutionResult:
    """Construct a structured assembly result with verification findings."""

    result_errors = list(errors or [])
    result_warnings = list(warnings or [])

    if assembly_path is not None and not assembly_path.exists():
        result_errors.append(f"Expected assembly file does not exist: {assembly_path}")
    if len(inserted_components) != expected_component_count:
        result_errors.append(
            f"Inserted component count {len(inserted_components)} did not match expected {expected_component_count}"
        )
    missing_files = [
        component_id
        for component_id, filepath in component_filepaths.items()
        if not filepath or filepath.startswith("<pending:")
    ]
    if missing_files:
        result_errors.append(f"Missing component file path for: {', '.join(sorted(missing_files))}")
    if not rebuild_attempted:
        result_warnings.append("Assembly rebuild was not attempted")
    if not save_checked:
        result_errors.append("Assembly save result was not checked")

    attempted_constraints = set(applied_constraint_ids) | {
        failed.constraint_id for failed in failed_constraints
    }
    missing_attempts = [constraint_id for constraint_id in planned_constraint_ids if constraint_id not in attempted_constraints]
    if missing_attempts:
        result_errors.append(f"Constraint operations were not attempted: {', '.join(missing_attempts)}")
    if failed_constraints:
        result_warnings.append(f"{len(failed_constraints)} constraint(s) failed")

    success = not result_errors and not failed_constraints
    status = "success" if success else "partial_failure" if assembly_path is not None else "failed"
    return AssemblyExecutionResult(
        success=success,
        status=status,
        assembly_path=str(assembly_path) if assembly_path is not None else None,
        inserted_components=inserted_components,
        applied_constraints=applied_constraint_ids,
        failed_constraints=failed_constraints,
        warnings=result_warnings,
        errors=result_errors,
    )


def result_to_summary_lines(result: AssemblyExecutionResult, expected_constraints: int) -> list[str]:
    """Create concise UI/API summary lines for an assembly result."""

    title = "Assembly created" if result.assembly_path else "Assembly not saved"
    if result.warnings or result.failed_constraints:
        title += " with warnings"
    lines = [title]
    lines.append(f"{len(result.inserted_components)} component(s) inserted")
    lines.append(f"{len(result.applied_constraints)} of {expected_constraints} constraint(s) applied")
    for failed in result.failed_constraints:
        lines.append(f"Failed constraint: {failed.constraint_id}")
    if result.assembly_path:
        lines.append("Output saved successfully")
    return lines
