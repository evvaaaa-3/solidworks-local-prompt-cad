"""High-level generic assembly planning and execution."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from cad_tools.assembly_planner import (
    AssemblyPlan,
    ConstraintSpec,
    build_assembly_plan,
    validate_assembly_plan,
)
from cad_tools.component_factory import ComponentBuildResult, create_components_for_plan
from config import mm_to_m, sanitize_filename
from solidworks_api.assembly import (
    create_new_assembly,
    fix_component,
    insert_component,
    save_assembly,
    set_component_position,
)
from solidworks_api.connection import connect_solidworks
from utils.output_paths import get_assemblies_output_dir


def create_assembly(
    assembly_type: str,
    parameters: dict[str, Any],
    dry_run: bool = True,
) -> dict[str, Any]:
    plan = build_assembly_plan(assembly_type, parameters)
    return execute_assembly_plan(plan, dry_run=dry_run)


def execute_assembly_plan(plan: AssemblyPlan, dry_run: bool = True) -> dict[str, Any]:
    validate_assembly_plan(plan)
    if dry_run:
        component_results = create_components_for_plan(plan, dry_run=True)
        print(f"[DRY CAD TOOL] Would create assembly from plan: {plan.assembly_type}.")
        return _result(
            plan=plan,
            status="dry_run_success",
            success=True,
            filepath=None,
            component_results=component_results,
            constraints_applied=[],
            constraints_failed=[],
            placement_fallback_used=_uses_coordinate_fallback(plan),
            message="Assembly dry-run completed.",
        )

    component_results = create_components_for_plan(plan, dry_run=False)
    assembly_model = _new_assembly_model()
    inserted_components = _insert_plan_instances(assembly_model, plan, component_results)
    constraints_applied, constraints_failed = _apply_constraints(
        assembly_model,
        plan,
        inserted_components,
    )
    return _save_plan_result(
        plan,
        assembly_model,
        component_results,
        constraints_applied,
        constraints_failed,
    )


def _new_assembly_model() -> Any:
    sw_app = connect_solidworks(visible=True)
    return create_new_assembly(sw_app)


def _insert_plan_instances(
    assembly_model: Any,
    plan: AssemblyPlan,
    component_results: dict[str, ComponentBuildResult],
) -> dict[str, Any]:
    inserted: dict[str, Any] = {}
    for instance in plan.instances:
        component_result = component_results[instance.component_id]
        x_mm, y_mm, z_mm = instance.position_mm
        component = insert_component(
            assembly_model,
            component_result.filepath,
            mm_to_m(x_mm),
            mm_to_m(y_mm),
            mm_to_m(z_mm),
        )
        set_component_position(component, mm_to_m(x_mm), mm_to_m(y_mm), mm_to_m(z_mm))
        inserted[instance.id] = component
    return inserted


def _apply_constraints(
    assembly_model: Any,
    plan: AssemblyPlan,
    inserted_components: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    applied: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for constraint in plan.constraints:
        if constraint.type == "coordinate_place":
            applied.append(_constraint_result(constraint, "coordinate placement fallback"))
            continue

        if constraint.type == "fixed":
            component = inserted_components.get(constraint.component_a)
            if component is None:
                failed.append(_constraint_result(constraint, "component was not inserted"))
                continue
            fix_component(assembly_model, component)
            applied.append(_constraint_result(constraint, "component fixed when supported"))
            continue

        failed.append(
            _constraint_result(
                constraint,
                "mate execution is planned but coordinate placement is used in this stage",
            )
        )
    return applied, failed


def _constraint_result(constraint: ConstraintSpec, message: str) -> dict[str, Any]:
    data = asdict(constraint)
    data["message"] = message
    return data


def _save_plan_result(
    plan: AssemblyPlan,
    assembly_model: Any,
    component_results: dict[str, ComponentBuildResult],
    constraints_applied: list[dict[str, Any]],
    constraints_failed: list[dict[str, Any]],
) -> dict[str, Any]:
    output_dir = get_assemblies_output_dir()
    filename = sanitize_filename(plan.output_filename)
    try:
        save_result = save_assembly(assembly_model, str(output_dir / filename))
    except RuntimeError as exc:
        return _result(
            plan=plan,
            status="save_failed",
            success=False,
            filepath=None,
            component_results=component_results,
            constraints_applied=constraints_applied,
            constraints_failed=constraints_failed,
            placement_fallback_used=_uses_coordinate_fallback(plan),
            message=str(exc),
        )

    filepath = Path(save_result["filepath"])
    return _result(
        plan=plan,
        status="success",
        success=True,
        filepath=filepath,
        component_results=component_results,
        constraints_applied=constraints_applied,
        constraints_failed=constraints_failed,
        placement_fallback_used=_uses_coordinate_fallback(plan),
        message="Assembly created successfully.",
    )


def _result(
    plan: AssemblyPlan,
    status: str,
    success: bool,
    filepath: Path | None,
    component_results: dict[str, ComponentBuildResult],
    constraints_applied: list[dict[str, Any]],
    constraints_failed: list[dict[str, Any]],
    placement_fallback_used: bool,
    message: str,
) -> dict[str, Any]:
    return {
        "success": success,
        "status": status,
        "operation": "create_assembly",
        "tool": "create_assembly",
        "assembly_type": plan.assembly_type,
        "filepath": str(filepath) if filepath is not None else None,
        "filename": filepath.name if filepath is not None else None,
        "output_dir": str(filepath.parent if filepath is not None else get_assemblies_output_dir()),
        "components": [_component_dict(result) for result in component_results.values()],
        "instances": [asdict(instance) for instance in plan.instances],
        "constraints_planned": [asdict(constraint) for constraint in plan.constraints],
        "constraints_applied": constraints_applied,
        "constraints_failed": constraints_failed,
        "placement_fallback_used": placement_fallback_used,
        "message": message,
    }


def _component_dict(result: ComponentBuildResult) -> dict[str, Any]:
    return {
        "id": result.component_id,
        "name": result.name,
        "type": result.type,
        "role": result.role,
        "filepath": result.filepath,
        "filename": result.filename,
        "instance_count": result.instance_count,
        "reused": result.reused,
    }


def _uses_coordinate_fallback(plan: AssemblyPlan) -> bool:
    return any(constraint.type == "coordinate_place" for constraint in plan.constraints)
