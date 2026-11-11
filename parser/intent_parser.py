"""Hybrid parser facade for rule, Ollama, and auto modes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from llm.intent_parser import parse_prompt_ollama
from nlp.preprocessor import NLPPreprocessResult, preprocess_prompt
from parser.rule_parser import parse_prompt_rule_based
from validator.validate_intent import validate_intent


ParserMode = Literal["rule", "ollama", "auto"]


@dataclass(frozen=True)
class ParseMetadata:
    parser_used: str
    confidence: float
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    clarification_required: bool = False
    clarification_message: str | None = None
    error_code: str | None = None
    error: str | None = None
    raw_prompt: str = ""
    normalized_prompt: str = ""
    preprocessing: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedIntentResult:
    success: bool
    parsed_intent: dict[str, Any] | None
    validated_intent: Any | None
    metadata: ParseMetadata


def parse_prompt_with_metadata(
    prompt: str,
    *,
    parser_mode: ParserMode = "rule",
    model_name: str | None = None,
) -> ParsedIntentResult:
    if parser_mode not in {"rule", "ollama", "auto"}:
        raise ValueError("parser_mode must be one of: rule, ollama, auto")

    try:
        preprocessing = preprocess_prompt(prompt)
    except ValueError as exc:
        return ParsedIntentResult(
            False,
            None,
            None,
            ParseMetadata(
                parser_used="nlp",
                confidence=0.0,
                error_code="invalid_prompt",
                error=str(exc),
                raw_prompt=prompt,
            ),
        )

    if parser_mode == "rule":
        return _parse_rule(preprocessing)
    if parser_mode == "ollama":
        return _parse_ollama(preprocessing, model_name=model_name)

    rule_result = _parse_rule(preprocessing)
    if rule_result.success and rule_result.metadata.confidence >= 0.95:
        return rule_result
    ollama_result = _parse_ollama(preprocessing, model_name=model_name)
    if ollama_result.success:
        return ollama_result
    warnings = list(rule_result.metadata.warnings)
    if rule_result.metadata.error:
        warnings.append(f"rule parser failed: {rule_result.metadata.error}")
    return ParsedIntentResult(
        False,
        None,
        None,
        ParseMetadata(
            parser_used="auto",
            confidence=0.0,
            warnings=warnings,
            missing_fields=ollama_result.metadata.missing_fields,
            clarification_required=ollama_result.metadata.clarification_required,
            clarification_message=ollama_result.metadata.clarification_message,
            error_code=ollama_result.metadata.error_code or rule_result.metadata.error_code,
            error=ollama_result.metadata.error or rule_result.metadata.error,
            raw_prompt=preprocessing.raw_prompt,
            normalized_prompt=preprocessing.normalized_prompt,
            preprocessing=preprocessing.metadata(),
        ),
    )


def _parse_rule(preprocessing: NLPPreprocessResult) -> ParsedIntentResult:
    parsed = None
    try:
        parsed = parse_prompt_rule_based(preprocessing.normalized_prompt, preprocessed=True)
        validated = validate_intent(parsed)
    except ValueError as exc:
        return ParsedIntentResult(
            False,
            parsed,
            None,
            ParseMetadata(
                parser_used="rule",
                confidence=0.0,
                error_code=_classify_rule_error(str(exc)),
                error=str(exc),
                clarification_required=_is_missing_dimension(str(exc)),
                clarification_message=str(exc) if _is_missing_dimension(str(exc)) else None,
                raw_prompt=preprocessing.raw_prompt,
                normalized_prompt=preprocessing.normalized_prompt,
                preprocessing=preprocessing.metadata(),
            ),
        )
    return ParsedIntentResult(
        True,
        parsed,
        validated,
        ParseMetadata(
            parser_used="rule",
            confidence=1.0,
            raw_prompt=preprocessing.raw_prompt,
            normalized_prompt=preprocessing.normalized_prompt,
            preprocessing=preprocessing.metadata(),
        ),
    )


def _parse_ollama(
    preprocessing: NLPPreprocessResult,
    *,
    model_name: str | None = None,
) -> ParsedIntentResult:
    result = parse_prompt_ollama(
        preprocessing.normalized_prompt,
        model_name=model_name,
        preprocessed=True,
    )
    if not result.success:
        return ParsedIntentResult(
            False,
            result.intent,
            None,
            ParseMetadata(
                parser_used="ollama",
                confidence=0.0,
                missing_fields=result.missing_fields,
                clarification_required=result.clarification_required,
                clarification_message=result.clarification_message,
                error_code=result.code,
                error=result.message,
                raw_prompt=preprocessing.raw_prompt,
                normalized_prompt=preprocessing.normalized_prompt,
                preprocessing=preprocessing.metadata(),
            ),
        )
    assert result.intent is not None
    return ParsedIntentResult(
        True,
        result.intent,
        validate_intent(result.intent),
        ParseMetadata(
            parser_used="ollama",
            confidence=0.85,
            raw_prompt=preprocessing.raw_prompt,
            normalized_prompt=preprocessing.normalized_prompt,
            preprocessing=preprocessing.metadata(),
        ),
    )


def _is_missing_dimension(message: str) -> bool:
    lowered = message.lower()
    return "missing" in lowered or "need" in lowered or "requires" in lowered


def _classify_rule_error(message: str) -> str:
    lowered = message.lower()
    if _is_missing_dimension(lowered):
        return "missing_dimension"
    if "unsupported" in lowered:
        return "unsupported_operation"
    return "schema_validation_failed"
