"""Request and response models for the local Prompt-to-CAD API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=1)


class ExecuteRequest(PromptRequest):
    mode: Literal["dry_run", "real"] = "dry_run"
    confirmed: bool = False


class ParseResponse(BaseModel):
    success: bool
    raw_prompt: str
    parsed_intent: dict[str, Any] | None = None
    validated_intent: dict[str, Any] | None = None
    error: str | None = None


class ExecuteResponse(BaseModel):
    success: bool
    mode: Literal["dry_run", "real"]
    raw_prompt: str
    parsed_intent: dict[str, Any] | None = None
    validated_intent: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    logs: list[str] = Field(default_factory=list)
    error: str | None = None


class OutputFile(BaseModel):
    filename: str
    file_type: str
    category: Literal["parts", "exports"]
    relative_path: str
    size_bytes: int
    modified_time: str
