"""High-level generic assembly planning and staged execution."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from cad_tools.cad_schemas import ConstraintExecutionError, TransformSpec
from cad_tools.assembly_planner import (
    AssemblyPlan,
    ConstraintSpec,
    build_assembly_plan,
    validate_assembly_plan,
)
from cad_tools.component_factory import ComponentBuildResult, create_components_for_plan
from cad_tools.face_placement import face_relative_component_origin, top_face_frame_from_box
from cad_tools.references import coerce_reference, resolve_component_reference
from cad_tools.transforms import has_rotation, transform_translation_m
from cad_tools.verification import build_assembly_execution_result, result_to_summary_lines
from config import mm_to_m, sanitize_filename
from solidworks_api.assembly import (
    create_new_assembly,
    fix_component,
    get_component_translation_mm,
    insert_component,
    save_assembly,
    set_component_transform,
)
from solidworks_api.connection import connect_solidworks
from solidworks_api.mates import apply_mate, rebuild_assembly
from solidworks_api.selection import SolidWorksReferenceResolver
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
    stages = ["validate_assembly_plan"]
    if dry_run:
        component_results = create_components_for_plan(plan, dry_run=True)
        stages.append("generate_or_locate_component_files")
        print(f"[DRY CAD TOOL] Would create assembly from plan: {plan.assembly_type}.")
        applied = [
            _constraint_result(constraint, "dry-run constraint validation completed")
            for constraint in plan.constraints
            if constraint.enabled
        ]
        return _result(
            plan=plan,
            status="dry_run_success",
            success=True,
            filepath=None,
            component_results=component_results,
            inserted_component_ids=[],
            constraints_applied=applied,
            constraints_failed=[],
            warnings=[],
            errors=[],
            stages=stages,
            verification_summary=["Assembly dry-run completed"],
            message="Assembly dry-run completed.",
        )

    component_results = create_components_for_plan(plan, dry_run=False)
    stages.append("generate_or_locate_component_files")
    _log_assembly_plan(plan)
    assembly_model = _new_assembly_model()
    stages.append("create_assembly_document")
    inserted_components, insertion_errors, transform_reports = _insert_plan_instances(
        assembly_model,
        plan,
        component_results,
    )
    stages.extend(["insert_component_instances", "apply_initial_transforms"])
    constraints_applied, constraints_failed = _apply_constraints(
        assembly_model,
        plan,
        inserted_components,
    )
    stages.extend(["resolve_references", "apply_mates_and_constraints"])
    rebuild_attempted = rebuild_assembly(assembly_model)
    stages.append("rebuild_assembly")
    return _save_plan_result(
        plan,
        assembly_model,
        component_results,
        list(inserted_components.keys()),
        constraints_applied,
        constraints_failed,
        stages,
        rebuild_attempted,
        insertion_errors,
        transform_reports,
    )


def _new_assembly_model() -> Any:
    sw_app = connect_solidworks(visible=True)
    return create_new_assembly(sw_app)


def _insert_plan_instances(
    assembly_model: Any,
    plan: AssemblyPlan,
    component_results: dict[str, ComponentBuildResult],
) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    inserted: dict[str, Any] = {}
    errors: list[str] = []
    transform_reports: list[dict[str, Any]] = []
    for instance in plan.instances:
        component_result = component_results[instance.component_id]
        if not component_result.filepath or component_result.filepath.startswith("<pending:"):
            errors.append(f"Instance {instance.id} has no component file path.")
            continue
        transform = _resolve_instance_transform(instance, inserted, plan)
        x_m, y_m, z_m = transform_translation_m(transform)
        try:
            component = insert_component(assembly_model, component_result.filepath, x_m, y_m, z_m)
            if has_rotation(transform):
                report = set_component_transform(component, transform)
            else:
                actual_mm = get_component_translation_mm(component)
                report = {
                    "applied": True,
                    "method": "insert_component_translation",
                    "requested_translation_mm": (
                        transform.translation_x,
                        transform.translation_y,
                        transform.translation_z,
                    ),
                    "actual_translation_mm": actual_mm,
                    "error": None,
                }
        except Exception as exc:
            errors.append(f"Instance {instance.id} insertion failed: {exc}")
            continue
        report.update(
            {
                "instance_id": instance.id,
                "component_id": instance.component_id,
                "component_filepath": component_result.filepath,
            }
        )
        if not report.get("applied", False):
            errors.append(f"Instance {instance.id} transform failed: {report.get('error')}")
        transform_reports.append(report)
        inserted[instance.id] = component
    return inserted, errors, transform_reports


def _resolve_instance_transform(
    instance: Any,
    inserted_components: dict[str, Any],
    plan: AssemblyPlan,
) -> Any:
    transform = instance.effective_transform()
    placement = getattr(instance, "placement", None)
    if placement is None:
        return transform
    target_instance = next(
        (candidate for candidate in plan.instances if candidate.id == placement.target_instance_id),
        None,
    )
    if target_instance is None or placement.target_instance_id not in inserted_components:
        raise ValueError(
            f"Placement for {instance.id} references target instance "
            f"{placement.target_instance_id} before it is inserted."
        )
    target_transform = target_instance.effective_transform()
    if placement.target_reference != "top_face":
        raise ValueError(f"Unsupported face-relative placement reference: {placement.target_reference}")
    frame = top_face_frame_from_box(target_transform)
    origin = face_relative_component_origin(frame, placement)
    return TransformSpec(
        translation_x=origin[0],
        translation_y=origin[1],
        translation_z=origin[2],
        rotation_x=transform.rotation_x,
        rotation_y=transform.rotation_y,
        rotation_z=transform.rotation_z,
    )


def _apply_constraints(
    assembly_model: Any,
    plan: AssemblyPlan,
    inserted_components: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    applied: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    resolver = SolidWorksReferenceResolver()
    for constraint in plan.constraints:
        if not constraint.enabled:
            continue
        if constraint.type == "coordinate_place":
            applied.append(_constraint_result(constraint, "legacy coordinate placement constraint skipped"))
            continue

        if constraint.type == "fixed":
            component = inserted_components.get(constraint.component_a)
            if component is None:
                failed.append(_constraint_error(constraint, "component was not inserted"))
                continue
            try:
                fix_component(assembly_model, component)
            except Exception as exc:
                failed.append(_constraint_error(constraint, "component fix failed", solidworks_error=str(exc)))
                continue
            applied.append(_constraint_result(constraint, "component fixed when supported"))
            continue

        component_a = inserted_components.get(constraint.component_a)
        component_b = inserted_components.get(constraint.component_b or "")
        if component_a is None or component_b is None:
            failed.append(_constraint_error(constraint, "one or more components were not inserted"))
            continue
        reference_a = None
        reference_b = None
        try:
            reference_a = coerce_reference(constraint.entity_a)
            reference_b = coerce_reference(constraint.entity_b)
            if reference_a is None or reference_b is None:
                raise ValueError("constraint references are required")
            resolve_component_reference(constraint.component_a, reference_a, component_a, resolver)
            resolve_component_reference(constraint.component_b or "", reference_b, component_b, resolver)
        except Exception as exc:
            failed.append(
                _constraint_error(
                    constraint,
                    "reference resolution failed",
                    failed_reference=reference_a or reference_b,
                    solidworks_error=str(exc),
                )
            )
            continue
        value_m = _constraint_value_m(constraint)
        mate_result = apply_mate(
            assembly_model,
            constraint_id=constraint.resolved_id(),
            constraint_type=constraint.type,
            alignment=constraint.alignment,
            value_m=value_m,
        )
        if mate_result.success:
            applied.append(_constraint_result(constraint, mate_result.message))
        else:
            failed.append(
                _constraint_error(
                    constraint,
                    mate_result.message,
                    solidworks_error=mate_result.solidworks_error,
                )
            )
    return applied, failed


def _constraint_result(constraint: ConstraintSpec, message: str) -> dict[str, Any]:
    data = _constraint_dict(constraint)
    data["message"] = message
    data["constraint_id"] = constraint.resolved_id()
    return data


def _constraint_error(
    constraint: ConstraintSpec,
    message: str,
    *,
    failed_reference: Any = None,
    solidworks_error: str | None = None,
) -> dict[str, Any]:
    return ConstraintExecutionError(
        constraint_id=constraint.resolved_id(),
        constraint_type=constraint.type,
        involved_components=[
            component
            for component in (constraint.component_a, constraint.component_b)
            if component
        ],
        failed_reference=failed_reference,
        message=message,
        solidworks_error=solidworks_error,
    ).model_dump()


def _constraint_value_m(constraint: ConstraintSpec) -> float:
    value = constraint.parameters.get("value")
    if value is None:
        value = constraint.parameters.get("distance_mm", 0.0)
    if constraint.type == "angle":
        return float(value)
    return mm_to_m(float(value))


def _save_plan_result(
    plan: AssemblyPlan,
    assembly_model: Any,
    component_results: dict[str, ComponentBuildResult],
    inserted_component_ids: list[str],
    constraints_applied: list[dict[str, Any]],
    constraints_failed: list[dict[str, Any]],
    stages: list[str],
    rebuild_attempted: bool,
    execution_errors: list[str],
    transform_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    output_dir = get_assemblies_output_dir()
    filename = sanitize_filename(plan.output_filename)
    save_checked = False
    try:
        save_result = save_assembly(assembly_model, str(output_dir / filename))
        save_checked = True
    except RuntimeError as exc:
        execution_errors.append(str(exc))
        verification = build_assembly_execution_result(
            assembly_path=None,
            expected_component_count=len(plan.instances),
            inserted_components=inserted_component_ids,
            planned_constraint_ids=_planned_constraint_ids(plan),
            applied_constraint_ids=[item["constraint_id"] for item in constraints_applied],
            failed_constraints=[ConstraintExecutionError(**item) for item in constraints_failed],
            component_filepaths={key: result.filepath for key, result in component_results.items()},
            rebuild_attempted=rebuild_attempted,
            save_checked=save_checked,
            errors=execution_errors,
        )
        return _result(
            plan=plan,
            status=verification.status,
            success=verification.success,
            filepath=None,
            component_results=component_results,
            inserted_component_ids=inserted_component_ids,
            constraints_applied=constraints_applied,
            constraints_failed=constraints_failed,
            warnings=verification.warnings,
            errors=verification.errors,
            stages=stages,
            verification_summary=result_to_summary_lines(verification, len(_planned_constraint_ids(plan))),
            transform_reports=transform_reports,
            message=str(exc),
        )

    filepath = Path(save_result["filepath"])
    stages.extend(["verify_component_count", "verify_mate_status", "save_assembly", "confirm_output_file_exists"])
    verification = build_assembly_execution_result(
        assembly_path=filepath,
        expected_component_count=len(plan.instances),
        inserted_components=inserted_component_ids,
        planned_constraint_ids=_planned_constraint_ids(plan),
        applied_constraint_ids=[item["constraint_id"] for item in constraints_applied],
        failed_constraints=[ConstraintExecutionError(**item) for item in constraints_failed],
        component_filepaths={key: result.filepath for key, result in component_results.items()},
        rebuild_attempted=rebuild_attempted,
        save_checked=save_checked,
        errors=execution_errors,
    )
    return _result(
        plan=plan,
        status=verification.status,
        success=verification.success,
        filepath=filepath,
        component_results=component_results,
        inserted_component_ids=inserted_component_ids,
        constraints_applied=constraints_applied,
        constraints_failed=constraints_failed,
        warnings=verification.warnings,
        errors=verification.errors,
        stages=stages,
        verification_summary=result_to_summary_lines(verification, len(_planned_constraint_ids(plan))),
        transform_reports=transform_reports,
        message="Assembly created successfully." if verification.success else "Assembly created with warnings.",
    )


def _result(
    plan: AssemblyPlan,
    status: str,
    success: bool,
    filepath: Path | None,
    component_results: dict[str, ComponentBuildResult],
    inserted_component_ids: list[str],
    constraints_applied: list[dict[str, Any]],
    constraints_failed: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
    stages: list[str],
    verification_summary: list[str],
    message: str,
    transform_reports: list[dict[str, Any]] | None = None,
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
        "instances": [_instance_dict(instance) for instance in plan.instances],
        "inserted_components": inserted_component_ids,
        "constraints_planned": [_constraint_dict(constraint) for constraint in plan.constraints if constraint.enabled],
        "constraints_applied": constraints_applied,
        "constraints_failed": constraints_failed,
        "applied_constraints": [item["constraint_id"] for item in constraints_applied],
        "failed_constraints": [item["constraint_id"] for item in constraints_failed],
        "warnings": warnings,
        "errors": errors,
        "execution_stages": stages,
        "verification_summary": verification_summary,
        "transform_reports": transform_reports or [],
        "assembly_plan_trace": _plan_trace(plan),
        "placement_fallback_used": _uses_coordinate_fallback(plan),
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
        "part_plan": result.part_plan,
        "features_executed": list(result.features_executed),
    }


def _instance_dict(instance: Any) -> dict[str, Any]:
    data = asdict(instance)
    transform = instance.effective_transform()
    data["transform"] = transform.model_dump()
    return data


def _constraint_dict(constraint: ConstraintSpec) -> dict[str, Any]:
    data = asdict(constraint)
    data["constraint_id"] = constraint.resolved_id()
    data["reference_a"] = coerce_reference(constraint.entity_a).model_dump() if constraint.entity_a else None
    data["reference_b"] = coerce_reference(constraint.entity_b).model_dump() if constraint.entity_b else None
    return data


def _planned_constraint_ids(plan: AssemblyPlan) -> list[str]:
    return [
        constraint.resolved_id()
        for constraint in plan.constraints
        if constraint.enabled and constraint.type != "coordinate_place"
    ]


def _uses_coordinate_fallback(plan: AssemblyPlan) -> bool:
    return any(constraint.type == "coordinate_place" for constraint in plan.constraints)


def _plan_trace(plan: AssemblyPlan) -> dict[str, Any]:
    return {
        "assembly_type": plan.assembly_type,
        "components": [asdict(component) for component in plan.components],
        "instances": [_instance_dict(instance) for instance in plan.instances],
        "constraints": [_constraint_dict(constraint) for constraint in plan.constraints if constraint.enabled],
        "metadata": plan.metadata,
    }


def _log_assembly_plan(plan: AssemblyPlan) -> None:
    print(f"[AssemblyPlan] type={plan.assembly_type}")
    for component in plan.components:
        print(f"[AssemblyPlan] component={asdict(component)}")
    for instance in plan.instances:
        transform = instance.effective_transform()
        print(
            "[AssemblyPlan] instance="
            f"{instance.id} component={instance.component_id} transform={transform.model_dump()}"
        )
    for constraint in plan.constraints:
        print(f"[AssemblyPlan] constraint={_constraint_dict(constraint)}")
