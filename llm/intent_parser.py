"""Ollama-backed intent parser with strict Pydantic validation gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from llm.intent_canonicalizer import canonicalize_intent
from llm.ollama_client import OllamaClient, OllamaError
from llm.prompt_templates import intent_system_prompt
from llm.response_parser import extract_json_object
from nlp.preprocessor import preprocess_prompt
from schemas.intent_schema import SUPPORTED_TOOL_NAMES
from validator.validate_intent import validate_intent


@dataclass(frozen=True)
class OllamaParseResult:
    success: bool
    intent: dict[str, Any] | None = None
    code: str | None = None
    message: str | None = None
    missing_fields: list[str] = field(default_factory=list)
    clarification_required: bool = False
    clarification_message: str | None = None
    normalized_prompt: str | None = None


def parse_prompt_ollama(
    prompt: str,
    *,
    model_name: str | None = None,
    client: OllamaClient | None = None,
    preprocessed: bool = False,
) -> OllamaParseResult:
    try:
        normalized_prompt = prompt if preprocessed else preprocess_prompt(prompt).normalized_prompt
    except ValueError as exc:
        return OllamaParseResult(False, code="invalid_prompt", message=str(exc))
    ollama = client or OllamaClient(model=model_name)
    try:
        raw = ollama.generate_json(normalized_prompt, intent_system_prompt())
    except OllamaError as exc:
        return OllamaParseResult(
            False,
            code=exc.code,
            message=str(exc),
            normalized_prompt=normalized_prompt,
        )

    try:
        parsed = extract_json_object(raw)
    except ValueError:
        return OllamaParseResult(
            False,
            code="invalid_json",
            message="Model returned malformed JSON.",
            normalized_prompt=normalized_prompt,
        )

    if parsed.get("clarification_required"):
        return OllamaParseResult(
            False,
            code="ambiguous_prompt",
            message=parsed.get("clarification_message") or "Clarification required.",
            missing_fields=list(parsed.get("missing_fields", [])),
            clarification_required=True,
            clarification_message=parsed.get("clarification_message"),
            normalized_prompt=normalized_prompt,
        )

    tool_name = parsed.get("tool_name")
    if tool_name not in SUPPORTED_TOOL_NAMES:
        return OllamaParseResult(
            False,
            code="unsupported_operation",
            message=f"Unsupported CAD tool: {tool_name!r}",
            intent=parsed,
            normalized_prompt=normalized_prompt,
        )

    parsed = canonicalize_intent(parsed)
    try:
        validate_intent(parsed)
    except ValueError as exc:
        return OllamaParseResult(
            False,
            code="schema_validation_failed",
            message=str(exc),
            intent=parsed,
            normalized_prompt=normalized_prompt,
        )
    return OllamaParseResult(True, intent=parsed, normalized_prompt=normalized_prompt)
