"""Generic component-feature-constraint assembly planning models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from cad_tools.cad_schemas import TransformSpec
from cad_tools.references import coerce_reference
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
FeatureType = Literal["boss_extrude", "cut_extrude", "hole", "through_hole", "fillet", "chamfer", "shell"]
ConstraintType = Literal[
    "fixed",
    "coincident",
    "concentric",
    "distance",
    "parallel",
    "angle",
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
SUPPORTED_FEATURE_TYPES = {"boss_extrude", "cut_extrude", "hole", "through_hole", "fillet", "chamfer", "shell"}
SUPPORTED_CONSTRAINT_TYPES = {
    "fixed",
    "coincident",
    "concentric",
    "distance",
    "parallel",
    "angle",
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
    material: str | None = None


@dataclass(frozen=True)
class ComponentInstanceSpec:
    id: str
    component_id: str
    instance_name: str
    position_mm: tuple[float, float, float]
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    role: str = ""
    transform: TransformSpec | None = None

    def effective_transform(self) -> TransformSpec:
        """Return explicit transform or convert legacy position/rotation fields."""

        if self.transform is not None:
            return self.transform
        x_mm, y_mm, z_mm = self.position_mm
        rx, ry, rz = self.rotation_deg
        return TransformSpec(
            translation_x=x_mm,
            translation_y=y_mm,
            translation_z=z_mm,
            rotation_x=rx,
            rotation_y=ry,
            rotation_z=rz,
        )


@dataclass(frozen=True)
class ConstraintSpec:
    type: ConstraintType
    component_a: str
    entity_a: str = ""
    component_b: str | None = None
    entity_b: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    required: bool = False
    constraint_id: str = ""
    alignment: str = "aligned"
    enabled: bool = True

    def resolved_id(self) -> str:
        """Return stable constraint id for execution and reporting."""

        if self.constraint_id:
            return self.constraint_id
        components = self.component_a if self.component_b is None else f"{self.component_a}_{self.component_b}"
        entity = self.entity_a or self.entity_b or "constraint"
        return f"{components}_{entity}_{self.type}"


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
        if not constraint.enabled:
            continue
        if constraint.type not in SUPPORTED_CONSTRAINT_TYPES:
            raise ValueError(f"Unsupported constraint type: {constraint.type}")
        if constraint.component_a not in valid_constraint_refs:
            raise ValueError(f"Constraint references unknown component/instance: {constraint.component_a}")
        if constraint.component_b and constraint.component_b not in valid_constraint_refs:
            raise ValueError(f"Constraint references unknown component/instance: {constraint.component_b}")
        if constraint.type not in {"fixed", "coordinate_place"}:
            if not constraint.component_b:
                raise ValueError(f"Constraint {constraint.resolved_id()} requires component_b.")
            try:
                coerce_reference(constraint.entity_a)
                coerce_reference(constraint.entity_b)
            except ValueError as exc:
                raise ValueError(f"Constraint {constraint.resolved_id()} has invalid reference: {exc}") from exc
        if constraint.type in {"distance", "angle"} and "value" not in constraint.parameters:
            legacy_value = "distance_mm" if constraint.type == "distance" else "angle_deg"
            if legacy_value not in constraint.parameters:
                raise ValueError(f"Constraint {constraint.resolved_id()} requires a value.")


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
    elif assembly_type == "flanged_shaft_assembly":
        plan = _build_flanged_shaft_assembly(parameters)
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
            ConstraintSpec("fixed", "base_plate_1", required=True, constraint_id="base_plate_fixed"),
            ConstraintSpec("coincident", "post_left", "bottom_face", "base_plate_1", "top_face", constraint_id="post_left_bottom_coincident"),
            ConstraintSpec("coincident", "post_right", "bottom_face", "base_plate_1", "top_face", constraint_id="post_right_bottom_coincident"),
            ConstraintSpec("parallel", "post_left", "axis", "post_right", "axis", constraint_id="posts_parallel"),
            ConstraintSpec(
                "distance",
                "post_left",
                "axis",
                "post_right",
                "axis",
                {"symmetric_about": "y_axis", "distance_mm": 70.0, "value": 70.0},
                constraint_id="posts_axis_distance",
            ),
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
            ConstraintSpec("fixed", "tube_1", required=True, constraint_id="tube_fixed"),
            ConstraintSpec("concentric", "cap_a", "axis", "tube_1", "axis", constraint_id="cap_a_tube_concentric"),
            ConstraintSpec("concentric", "cap_b", "axis", "tube_1", "axis", constraint_id="cap_b_tube_concentric"),
            ConstraintSpec("coincident", "cap_a", "inner_face", "tube_1", "end_a", constraint_id="cap_a_end_coincident"),
            ConstraintSpec("coincident", "cap_b", "inner_face", "tube_1", "end_b", constraint_id="cap_b_end_coincident"),
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
            ConstraintSpec("fixed", "shaft_1", required=True, constraint_id="shaft_fixed"),
            ConstraintSpec("concentric", "wheel_left", "axis", "shaft_1", "axis", constraint_id="wheel_left_concentric"),
            ConstraintSpec("concentric", "wheel_right", "axis", "shaft_1", "axis", constraint_id="wheel_right_concentric"),
            ConstraintSpec("distance", "wheel_left", "center", "shaft_1", "end_a", {"near_end": "A", "value": offset}, constraint_id="wheel_left_end_distance"),
            ConstraintSpec("distance", "wheel_right", "center", "shaft_1", "end_b", {"near_end": "B", "value": offset}, constraint_id="wheel_right_end_distance"),
        ),
        output_filename="simple_shaft_with_two_wheels.SLDASM",
        metadata={"description": "Simple shaft with two wheels"},
    )


def _build_flanged_shaft_assembly(parameters: dict[str, Any]) -> AssemblyPlan:
    shaft_length = parameters.get("shaft_length_mm", 120.0)
    flange_thickness = parameters.get("flange_thickness_mm", 12.0)
    hub_thickness = parameters.get("hub_thickness_mm", 16.0)
    flange_offset = (shaft_length - flange_thickness) / 4.0
    hub_offset = -(shaft_length - hub_thickness) / 4.0
    return AssemblyPlan(
        assembly_type="flanged_shaft_assembly",
        components=(
            ComponentSpec(
                id="shaft",
                type="shaft",
                role="shaft",
                dimensions={
                    "diameter_mm": parameters.get("shaft_diameter_mm", 16.0),
                    "length_mm": shaft_length,
                },
            ),
            ComponentSpec(
                id="flange",
                type="disc",
                role="flange",
                dimensions={
                    "diameter_mm": parameters.get("flange_diameter_mm", 70.0),
                    "thickness_mm": flange_thickness,
                },
                features=(
                    FeatureSpec(
                        type="hole",
                        dimensions={"diameter_mm": parameters.get("shaft_diameter_mm", 16.0)},
                        name="shaft_clearance_hole",
                    ),
                ),
            ),
            ComponentSpec(
                id="hub",
                type="disc",
                role="supporting_hub",
                dimensions={
                    "diameter_mm": parameters.get("hub_diameter_mm", 42.0),
                    "thickness_mm": hub_thickness,
                },
            ),
        ),
        instances=(
            ComponentInstanceSpec("shaft_1", "shaft", "shaft", (0.0, 0.0, 0.0), role="shaft"),
            ComponentInstanceSpec("flange_1", "flange", "flange", (0.0, 0.0, flange_offset), role="flange"),
            ComponentInstanceSpec("hub_1", "hub", "hub", (0.0, 0.0, hub_offset), role="supporting_hub"),
        ),
        constraints=(
            ConstraintSpec("fixed", "shaft_1", required=True, constraint_id="shaft_fixed"),
            ConstraintSpec("concentric", "flange_1", "axis", "shaft_1", "axis", constraint_id="flange_shaft_concentric"),
            ConstraintSpec("coincident", "flange_1", "inner_face", "shaft_1", "end_b", constraint_id="flange_shaft_coincident"),
            ConstraintSpec("concentric", "hub_1", "axis", "shaft_1", "axis", constraint_id="hub_shaft_concentric"),
            ConstraintSpec("distance", "hub_1", "center", "flange_1", "center", {"value": abs(flange_offset - hub_offset)}, constraint_id="hub_flange_distance"),
        ),
        output_filename="flanged_shaft_assembly.SLDASM",
        metadata={"description": "Flanged shaft assembly with hub support"},
    )
