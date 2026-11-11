"""Request and response models for the local Prompt-to-CAD API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=1)
    parser_mode: Literal["rule", "ollama", "auto"] = "rule"
    model_name: str | None = None


class ExecuteRequest(PromptRequest):
    mode: Literal["dry_run", "real"] = "dry_run"
    confirmed: bool = False
    dry_run: bool | None = None


class ParseResponse(BaseModel):
    success: bool
    raw_prompt: str
    normalized_prompt: str | None = None
    preprocessing: dict[str, Any] = Field(default_factory=dict)
    parsed_intent: dict[str, Any] | None = None
    validated_intent: dict[str, Any] | None = None
    parser_used: str | None = None
    confidence: float | None = None
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    clarification_required: bool = False
    clarification_message: str | None = None
    validation_status: str | None = None
    error: str | None = None


class ExecuteResponse(BaseModel):
    success: bool
    mode: Literal["dry_run", "real"]
    raw_prompt: str
    normalized_prompt: str | None = None
    preprocessing: dict[str, Any] = Field(default_factory=dict)
    parsed_intent: dict[str, Any] | None = None
    validated_intent: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    logs: list[str] = Field(default_factory=list)
    parser_used: str | None = None
    confidence: float | None = None
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    clarification_required: bool = False
    clarification_message: str | None = None
    validation_status: str | None = None
    execution_verification: dict[str, Any] | None = None
    error: str | None = None


class OutputFile(BaseModel):
    filename: str
    file_type: str
    category: Literal["parts", "exports", "assemblies"]
    relative_path: str
    size_bytes: int
    modified_time: str
