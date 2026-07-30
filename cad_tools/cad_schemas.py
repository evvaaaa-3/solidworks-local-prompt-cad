"""Pydantic schemas for generic CAD feature, transform, reference, and mate plans."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


FeatureType = Literal[
    "boss_extrude",
    "cut_extrude",
    "hole",
    "fillet",
    "chamfer",
    "shell",
]
FutureFeatureType = Literal["revolve", "sweep", "loft", "mirror", "pattern", "thread"]
ReferenceEntityType = Literal[
    "component_origin",
    "front_plane",
    "top_plane",
    "right_plane",
    "cylindrical_face",
    "planar_face",
    "circular_edge",
    "outer_edge",
    "face_normal_direction",
    "feature_face",
    "feature_edge",
    "axis",
    "center",
]
ConstraintType = Literal["fixed", "coincident", "concentric", "distance", "parallel", "angle"]
AlignmentType = Literal["aligned", "anti_aligned", "closest", "opposed"]


class ReferenceSpec(BaseModel):
    """Declarative selector for a model, component, face, edge, plane, or axis."""

    model_config = ConfigDict(extra="forbid")

    entity_type: ReferenceEntityType
    feature_id: str | None = None
    reference_name: str | None = None
    selection_rule: str | None = None
    direction: tuple[float, float, float] | None = None


class FeatureSpec(BaseModel):
    """Structured feature operation in a reusable part modelling sequence."""

    model_config = ConfigDict(extra="forbid")

    feature_id: str
    feature_type: FeatureType
    parameters: dict[str, Any] = Field(default_factory=dict)
    reference_geometry: list[ReferenceSpec] = Field(default_factory=list)
    operation_order: int = Field(ge=0)
    enabled: bool = True

    @field_validator("feature_id")
    @classmethod
    def validate_feature_id(cls, value: str) -> str:
        feature_id = value.strip()
        if not feature_id:
            raise ValueError("feature_id cannot be empty")
        return feature_id

    @model_validator(mode="after")
    def validate_parameters(self) -> "FeatureSpec":
        required = {
            "boss_extrude": ("depth_mm",),
            "cut_extrude": (),
            "hole": ("diameter_mm",),
            "fillet": ("radius_mm",),
            "chamfer": ("distance_mm",),
            "shell": ("thickness_mm",),
        }[self.feature_type]
        for name in required:
            value = self.parameters.get(name)
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"{self.feature_id} requires positive {name}")
        return self


class PartPlan(BaseModel):
    """Declarative part plan made of a base feature plus ordered feature operations."""

    model_config = ConfigDict(extra="forbid")

    part_name: str
    units: Literal["mm"] = "mm"
    base_feature: FeatureSpec
    features: list[FeatureSpec] = Field(default_factory=list)
    material: str | None = None
    output_filename: str

    @field_validator("part_name", "output_filename")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("value cannot be empty")
        return text

    @model_validator(mode="after")
    def validate_feature_ids_and_filename(self) -> "PartPlan":
        feature_ids = [self.base_feature.feature_id] + [feature.feature_id for feature in self.features]
        if len(set(feature_ids)) != len(feature_ids):
            raise ValueError("PartPlan feature ids must be unique")
        if Path(self.output_filename).name != self.output_filename:
            raise ValueError("output_filename must not include a path")
        if not self.output_filename.lower().endswith(".sldprt"):
            raise ValueError("PartPlan output_filename must end with .SLDPRT")
        return self

    def ordered_features(self) -> list[FeatureSpec]:
        """Return enabled feature operations sorted by operation order."""

        return sorted(
            [self.base_feature, *self.features],
            key=lambda feature: (feature.operation_order, feature.feature_id),
        )


class TransformSpec(BaseModel):
    """Rigid transform in planner units: millimetres for translation, degrees for rotation."""

    model_config = ConfigDict(extra="forbid")

    translation_x: float = 0.0
    translation_y: float = 0.0
    translation_z: float = 0.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0

    @field_validator("rotation_x", "rotation_y", "rotation_z")
    @classmethod
    def validate_rotation(cls, value: float) -> float:
        if value < -360.0 or value > 360.0:
            raise ValueError("rotation values are degrees and must be between -360 and 360")
        return value


class ConstraintSpec(BaseModel):
    """Declarative assembly mate or fixed constraint."""

    model_config = ConfigDict(extra="forbid")

    constraint_id: str
    constraint_type: ConstraintType
    component_a: str
    reference_a: ReferenceSpec | None = None
    component_b: str | None = None
    reference_b: ReferenceSpec | None = None
    value: float | None = None
    alignment: AlignmentType = "aligned"
    enabled: bool = True
    required: bool = False

    @field_validator("constraint_id", "component_a")
    @classmethod
    def validate_id(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("constraint ids and component refs cannot be empty")
        return text

    @model_validator(mode="after")
    def validate_refs(self) -> "ConstraintSpec":
        if self.constraint_type == "fixed":
            return self
        if not self.component_b:
            raise ValueError(f"{self.constraint_id} requires component_b")
        if self.reference_a is None or self.reference_b is None:
            raise ValueError(f"{self.constraint_id} requires reference_a and reference_b")
        if self.constraint_type in {"distance", "angle"} and self.value is None:
            raise ValueError(f"{self.constraint_id} requires value")
        return self


class ConstraintExecutionError(BaseModel):
    """Structured failure returned when a mate or reference cannot be completed."""

    model_config = ConfigDict(extra="forbid")

    constraint_id: str
    constraint_type: str
    involved_components: list[str]
    failed_reference: ReferenceSpec | None = None
    message: str
    solidworks_error: str | None = None


class AssemblyExecutionResult(BaseModel):
    """Structured result for assembly execution and verification."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    status: str
    assembly_path: str | None = None
    inserted_components: list[str] = Field(default_factory=list)
    applied_constraints: list[str] = Field(default_factory=list)
    failed_constraints: list[ConstraintExecutionError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
