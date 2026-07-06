"""Pydantic schemas for Stage 1 CAD intents."""

from __future__ import annotations

import re
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PositiveMillimeters = Annotated[float, Field(gt=0)]
_SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9_. -]+$")


class CubeParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    side_mm: PositiveMillimeters


class BlockParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length_mm: PositiveMillimeters
    width_mm: PositiveMillimeters
    height_mm: PositiveMillimeters


class CylinderParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diameter_mm: PositiveMillimeters
    height_mm: PositiveMillimeters


class DiscParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diameter_mm: PositiveMillimeters
    thickness_mm: PositiveMillimeters


class PlateParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length_mm: PositiveMillimeters
    width_mm: PositiveMillimeters
    thickness_mm: PositiveMillimeters


class TubeParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outer_diameter_mm: PositiveMillimeters
    inner_diameter_mm: PositiveMillimeters
    height_mm: PositiveMillimeters

    @model_validator(mode="after")
    def validate_diameters(self) -> "TubeParameters":
        if self.outer_diameter_mm <= self.inner_diameter_mm:
            raise ValueError("outer_diameter_mm must be greater than inner_diameter_mm")
        return self


class PlateWithHoleParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length_mm: PositiveMillimeters
    width_mm: PositiveMillimeters
    thickness_mm: PositiveMillimeters
    hole_diameter_mm: PositiveMillimeters

    @model_validator(mode="after")
    def validate_hole_size(self) -> "PlateWithHoleParameters":
        if self.hole_diameter_mm >= self.length_mm or self.hole_diameter_mm >= self.width_mm:
            raise ValueError("hole_diameter_mm must be smaller than length_mm and width_mm")
        return self


class ConeParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_diameter_mm: PositiveMillimeters
    height_mm: PositiveMillimeters


class SphereParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diameter_mm: PositiveMillimeters


class TorusParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    major_diameter_mm: PositiveMillimeters
    minor_diameter_mm: PositiveMillimeters

    @model_validator(mode="after")
    def validate_torus_geometry(self) -> "TorusParameters":
        if self.major_diameter_mm <= self.minor_diameter_mm:
            raise ValueError("major_diameter_mm must be greater than minor_diameter_mm")
        return self


class ExportStepParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        filename = value.strip()
        if not filename:
            raise ValueError("filename cannot be empty")
        if "/" in filename or "\\" in filename or ":" in filename:
            raise ValueError("filename must not contain paths or drive letters")
        if ".." in filename:
            raise ValueError("filename must not contain '..'")
        if not filename.lower().endswith((".step", ".stp")):
            raise ValueError("STEP filename must end with .step or .stp")
        if not _SAFE_FILENAME_PATTERN.fullmatch(filename):
            raise ValueError("filename contains unsupported characters")
        return filename


class CubeIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["create_cube"]
    parameters: CubeParameters


class BlockIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["create_block"]
    parameters: BlockParameters


class CylinderIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["create_cylinder"]
    parameters: CylinderParameters


class DiscIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["create_disc"]
    parameters: DiscParameters


class PlateIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["create_plate"]
    parameters: PlateParameters


class TubeIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["create_tube"]
    parameters: TubeParameters


class PlateWithHoleIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["create_plate_with_hole"]
    parameters: PlateWithHoleParameters


class ConeIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["create_cone"]
    parameters: ConeParameters


class SphereIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["create_sphere"]
    parameters: SphereParameters


class TorusIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["create_torus"]
    parameters: TorusParameters


class ExportStepIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["export_step"]
    parameters: ExportStepParameters


Intent = Annotated[
    Union[
        CubeIntent,
        BlockIntent,
        CylinderIntent,
        DiscIntent,
        PlateIntent,
        TubeIntent,
        PlateWithHoleIntent,
        ConeIntent,
        SphereIntent,
        TorusIntent,
        ExportStepIntent,
    ],
    Field(discriminator="tool_name"),
]
