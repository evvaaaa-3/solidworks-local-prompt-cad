"""Generic component-feature-constraint assembly planning models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from config import sanitize_filename


ComponentType = Literal[
    "plate",
    "plate_with_hole",
    "cylinder",
    "tube",
    "disc",
    "shaft",
    "wheel",
    "pin",
]
FeatureType = Literal["hole", "through_hole"]
ConstraintType = Literal[
    "fixed",
    "coincident",
    "concentric",
    "distance",
    "parallel",
    "coordinate_place",
]

SUPPORTED_COMPONENT_TYPES = {
    "plate",
    "plate_with_hole",
    "cylinder",
    "tube",
    "disc",
    "shaft",
    "wheel",
    "pin",
}
SUPPORTED_FEATURE_TYPES = {"hole", "through_hole"}
SUPPORTED_CONSTRAINT_TYPES = {
    "fixed",
    "coincident",
    "concentric",
    "distance",
    "parallel",
    "coordinate_place",
}


@dataclass(frozen=True)
class FeatureSpec:
    type: FeatureType
    dimensions: dict[str, float]
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    name: str = ""


@dataclass(frozen=True)
class ComponentSpec:
    id: str
    type: ComponentType
    dimensions: dict[str, float]
    features: tuple[FeatureSpec, ...] = ()
    role: str = ""
    quantity: int = 1
    reuse_part: bool = True


@dataclass(frozen=True)
class ComponentInstanceSpec:
    id: str
    component_id: str
    instance_name: str
    position_mm: tuple[float, float, float]
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    role: str = ""


@dataclass(frozen=True)
class ConstraintSpec:
    type: ConstraintType
    component_a: str
    entity_a: str = ""
    component_b: str | None = None
    entity_b: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    required: bool = False


@dataclass(frozen=True)
class AssemblyPlan:
    assembly_type: str
    components: tuple[ComponentSpec, ...]
    instances: tuple[ComponentInstanceSpec, ...]
    constraints: tuple[ConstraintSpec, ...]
    output_filename: str
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_assembly_plan(plan: AssemblyPlan) -> None:
    component_ids = {component.id for component in plan.components}
    if len(component_ids) != len(plan.components):
        raise ValueError("AssemblyPlan component ids must be unique.")
    if not component_ids:
        raise ValueError("AssemblyPlan needs at least one component.")

    instance_ids = {instance.id for instance in plan.instances}
    if len(instance_ids) != len(plan.instances):
        raise ValueError("AssemblyPlan instance ids must be unique.")
    if not instance_ids:
        raise ValueError("AssemblyPlan needs at least one component instance.")

    safe_filename = sanitize_filename(plan.output_filename)
    if not safe_filename.lower().endswith(".sldasm") or safe_filename != plan.output_filename:
        raise ValueError("AssemblyPlan output filename must be a safe .SLDASM filename.")

    for component in plan.components:
        if component.type not in SUPPORTED_COMPONENT_TYPES:
            raise ValueError(f"Unsupported component type: {component.type}")
        if component.quantity < 1:
            raise ValueError("Component quantity must be at least 1.")
        _validate_positive_dimensions(component.dimensions, f"component {component.id}")
        for feature in component.features:
            if feature.type not in SUPPORTED_FEATURE_TYPES:
                raise ValueError(f"Unsupported feature type: {feature.type}")
            _validate_positive_dimensions(feature.dimensions, f"feature {feature.name or feature.type}")

    for instance in plan.instances:
        if instance.component_id not in component_ids:
            raise ValueError(f"Instance {instance.id} references unknown component {instance.component_id}.")

    valid_constraint_refs = component_ids | instance_ids
    for constraint in plan.constraints:
        if constraint.type not in SUPPORTED_CONSTRAINT_TYPES:
            raise ValueError(f"Unsupported constraint type: {constraint.type}")
        if constraint.component_a not in valid_constraint_refs:
            raise ValueError(f"Constraint references unknown component/instance: {constraint.component_a}")
        if constraint.component_b and constraint.component_b not in valid_constraint_refs:
            raise ValueError(f"Constraint references unknown component/instance: {constraint.component_b}")


def _validate_positive_dimensions(dimensions: dict[str, float], label: str) -> None:
    for name, value in dimensions.items():
        if isinstance(value, (int, float)) and value <= 0:
            raise ValueError(f"{label} dimension {name} must be positive.")


def build_assembly_plan(assembly_type: str, parameters: dict[str, Any]) -> AssemblyPlan:
    if assembly_type == "base_plate_with_cylinders":
        plan = _build_base_plate_with_cylinders(parameters)
    elif assembly_type == "tube_with_two_end_discs":
        plan = _build_tube_with_two_end_discs(parameters)
    elif assembly_type == "simple_shaft_with_two_wheels":
        plan = _build_simple_shaft_with_two_wheels(parameters)
    else:
        raise ValueError(f"Unsupported assembly type: {assembly_type}")
    validate_assembly_plan(plan)
    return plan


def _build_base_plate_with_cylinders(parameters: dict[str, Any]) -> AssemblyPlan:
    z_mm = (parameters["base_thickness_mm"] + parameters["post_height_mm"]) / 2.0
    return AssemblyPlan(
        assembly_type="base_plate_with_cylinders",
        components=(
            ComponentSpec(
                id="base_plate",
                type="plate",
                role="base",
                dimensions={
                    "length_mm": parameters["base_length_mm"],
                    "width_mm": parameters["base_width_mm"],
                    "thickness_mm": parameters["base_thickness_mm"],
                },
            ),
            ComponentSpec(
                id="post",
                type="cylinder",
                role="post",
                quantity=int(parameters["post_count"]),
                dimensions={
                    "diameter_mm": parameters["post_diameter_mm"],
                    "height_mm": parameters["post_height_mm"],
                },
            ),
        ),
        instances=(
            ComponentInstanceSpec("base_plate_1", "base_plate", "base_plate", (0.0, 0.0, 0.0), role="base"),
            ComponentInstanceSpec("post_left", "post", "post_left", (-35.0, 0.0, z_mm), role="post"),
            ComponentInstanceSpec("post_right", "post", "post_right", (35.0, 0.0, z_mm), role="post"),
        ),
        constraints=(
            ConstraintSpec("fixed", "base_plate_1", required=True),
            ConstraintSpec("coincident", "post_left", "bottom_face", "base_plate_1", "top_face"),
            ConstraintSpec("coincident", "post_right", "bottom_face", "base_plate_1", "top_face"),
            ConstraintSpec(
                "distance",
                "post_left",
                "axis",
                "post_right",
                "axis",
                {"symmetric_about": "y_axis", "distance_mm": 70.0},
            ),
            ConstraintSpec("coordinate_place", "base_plate_1", parameters={"position_mm": (0.0, 0.0, 0.0)}),
            ConstraintSpec("coordinate_place", "post_left", parameters={"position_mm": (-35.0, 0.0, z_mm)}),
            ConstraintSpec("coordinate_place", "post_right", parameters={"position_mm": (35.0, 0.0, z_mm)}),
        ),
        output_filename="base_plate_with_cylinders.SLDASM",
        metadata={"description": "Base plate with two cylindrical posts"},
    )


def _build_tube_with_two_end_discs(parameters: dict[str, Any]) -> AssemblyPlan:
    offset = (parameters["tube_height_mm"] + parameters["cap_thickness_mm"]) / 2.0
    return AssemblyPlan(
        assembly_type="tube_with_two_end_discs",
        components=(
            ComponentSpec(
                id="tube",
                type="tube",
                role="body",
                dimensions={
                    "outer_diameter_mm": parameters["tube_outer_diameter_mm"],
                    "inner_diameter_mm": parameters["tube_inner_diameter_mm"],
                    "height_mm": parameters["tube_height_mm"],
                },
            ),
            ComponentSpec(
                id="cap",
                type="disc",
                role="end_cap",
                quantity=int(parameters["cap_count"]),
                dimensions={
                    "diameter_mm": parameters["cap_diameter_mm"],
                    "thickness_mm": parameters["cap_thickness_mm"],
                },
            ),
        ),
        instances=(
            ComponentInstanceSpec("tube_1", "tube", "tube", (0.0, 0.0, 0.0), role="body"),
            ComponentInstanceSpec("cap_a", "cap", "cap_a", (0.0, 0.0, -offset), role="end_cap"),
            ComponentInstanceSpec("cap_b", "cap", "cap_b", (0.0, 0.0, offset), role="end_cap"),
        ),
        constraints=(
            ConstraintSpec("fixed", "tube_1", required=True),
            ConstraintSpec("concentric", "cap_a", "axis", "tube_1", "axis"),
            ConstraintSpec("concentric", "cap_b", "axis", "tube_1", "axis"),
            ConstraintSpec("coincident", "cap_a", "inner_face", "tube_1", "end_a"),
            ConstraintSpec("coincident", "cap_b", "inner_face", "tube_1", "end_b"),
            ConstraintSpec("coordinate_place", "tube_1", parameters={"position_mm": (0.0, 0.0, 0.0)}),
            ConstraintSpec("coordinate_place", "cap_a", parameters={"position_mm": (0.0, 0.0, -offset)}),
            ConstraintSpec("coordinate_place", "cap_b", parameters={"position_mm": (0.0, 0.0, offset)}),
        ),
        output_filename="tube_with_two_end_discs.SLDASM",
        metadata={"description": "Tube with two circular end caps"},
    )


def _build_simple_shaft_with_two_wheels(parameters: dict[str, Any]) -> AssemblyPlan:
    offset = (parameters["shaft_length_mm"] - parameters["wheel_thickness_mm"]) / 2.0
    return AssemblyPlan(
        assembly_type="simple_shaft_with_two_wheels",
        components=(
            ComponentSpec(
                id="shaft",
                type="shaft",
                role="shaft",
                dimensions={
                    "diameter_mm": parameters["shaft_diameter_mm"],
                    "length_mm": parameters["shaft_length_mm"],
                },
            ),
            ComponentSpec(
                id="wheel",
                type="wheel",
                role="wheel",
                quantity=int(parameters["wheel_count"]),
                dimensions={
                    "diameter_mm": parameters["wheel_diameter_mm"],
                    "thickness_mm": parameters["wheel_thickness_mm"],
                },
            ),
        ),
        instances=(
            ComponentInstanceSpec("shaft_1", "shaft", "shaft", (0.0, 0.0, 0.0), role="shaft"),
            ComponentInstanceSpec("wheel_left", "wheel", "wheel_left", (0.0, 0.0, -offset), role="wheel"),
            ComponentInstanceSpec("wheel_right", "wheel", "wheel_right", (0.0, 0.0, offset), role="wheel"),
        ),
        constraints=(
            ConstraintSpec("fixed", "shaft_1", required=True),
            ConstraintSpec("concentric", "wheel_left", "axis", "shaft_1", "axis"),
            ConstraintSpec("concentric", "wheel_right", "axis", "shaft_1", "axis"),
            ConstraintSpec("distance", "wheel_left", "center", "shaft_1", "end_a", {"near_end": "A"}),
            ConstraintSpec("distance", "wheel_right", "center", "shaft_1", "end_b", {"near_end": "B"}),
            ConstraintSpec("coordinate_place", "shaft_1", parameters={"position_mm": (0.0, 0.0, 0.0)}),
            ConstraintSpec("coordinate_place", "wheel_left", parameters={"position_mm": (0.0, 0.0, -offset)}),
            ConstraintSpec("coordinate_place", "wheel_right", parameters={"position_mm": (0.0, 0.0, offset)}),
        ),
        output_filename="simple_shaft_with_two_wheels.SLDASM",
        metadata={"description": "Simple shaft with two wheels"},
    )
