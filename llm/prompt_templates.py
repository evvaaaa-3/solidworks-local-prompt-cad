"""Prompt templates and supported capability lists for Ollama parsing."""

from __future__ import annotations

from cad_tools.assembly_planner import SUPPORTED_CONSTRAINT_TYPES
from schemas.intent_schema import SUPPORTED_TOOL_NAMES, TOOL_PARAMETER_MODELS


def intent_system_prompt() -> str:
    tools = ", ".join(SUPPORTED_TOOL_NAMES)
    contracts = "; ".join(
        f"{tool_name}: {', '.join(parameter_model.model_fields)}"
        for tool_name, parameter_model in TOOL_PARAMETER_MODELS.items()
    )
    constraints = ", ".join(sorted(SUPPORTED_CONSTRAINT_TYPES - {"coordinate_place"}))
    return (
        "You convert CAD requests into JSON only. Do not use Markdown, code, or explanations. "
        "The prompt has already been normalized by deterministic NLP preprocessing. "
        "Lengths are millimetres; do not convert them again. User-facing angles are degrees. "
        f"Supported tool_name values: {tools}. "
        f"Exact parameter field names by tool: {contracts}. "
        "Use these field names exactly, including every _mm suffix. "
        f"Supported assembly constraints: {constraints}. "
        "Use only supported operations. Never invent COM methods or CAD feature types. "
        "Never emit Python, shell commands, file paths, or executable code. "
        "If critical dimensions are missing, return "
        "{\"clarification_required\": true, \"missing_fields\": [...], \"clarification_message\": \"...\"}. "
        "Otherwise return {\"tool_name\": \"...\", \"parameters\": {...}}."
    )
