"""Pydantic schemas for Stage 1 CAD intents."""

from __future__ import annotations

import re
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class ExportStepIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["export_step"]
    parameters: ExportStepParameters


Intent = Annotated[
    Union[CubeIntent, BlockIntent, CylinderIntent, ExportStepIntent],
    Field(discriminator="tool_name"),
]
