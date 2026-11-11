"""Safe NLP preprocessing before rule-based or Ollama intent parsing."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache
import re
from typing import Any

from nlp.units import Measurement, extract_measurements as _extract_measurements
from nlp.units import normalize_number_words, normalize_units as _normalize_units


@dataclass(frozen=True)
class QuantityPhrase:
    quantity: int
    noun: str


@dataclass(frozen=True)
class NLPPreprocessResult:
    raw_prompt: str
    normalized_prompt: str
    measurements: list[Measurement] = field(default_factory=list)
    quantities: list[QuantityPhrase] = field(default_factory=list)
    nlp_engine: str = "deterministic_fallback"
    diagnostics: list[str] = field(default_factory=list)

    def metadata(self) -> dict[str, Any]:
        return {
            "raw_prompt": self.raw_prompt,
            "normalized_prompt": self.normalized_prompt,
            "measurements": [asdict(item) for item in self.measurements],
            "quantities": [asdict(item) for item in self.quantities],
            "nlp_engine": self.nlp_engine,
            "diagnostics": list(self.diagnostics),
        }


_UNIT_WORDS = {
    "mm", "millimeter", "millimeters", "millimetre", "millimetres",
    "cm", "centimeter", "centimeters", "centimetre", "centimetres",
    "m", "meter", "meters", "metre", "metres",
}
_FILLER_PATTERNS = (
    r"\bmake\s+me\s+(?:a|an)\b",
    r"\bgive\s+me\s+(?:a|an)\b",
    r"\bi\s+(?:would\s+like|want)\b",
    r"\bplease\b",
    r"\bthat\s*(?:is|'s)\b",
)


def preprocess_prompt(text: str) -> NLPPreprocessResult:
    """Return normalized engineering text and non-executable NLP metadata."""

    raw_prompt = text
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Prompt cannot be empty.")

    tokenized, engine, diagnostics = _linguistic_normalize(text)
    numbered = normalize_number_words(tokenized)
    measurements = _extract_measurements(numbered)
    unit_normalized = _normalize_units(numbered)
    cleaned = clean_engineering_text(unit_normalized)
    quantities = extract_quantity_phrases(cleaned)
    return NLPPreprocessResult(
        raw_prompt=raw_prompt,
        normalized_prompt=cleaned,
        measurements=measurements,
        quantities=quantities,
        nlp_engine=engine,
        diagnostics=diagnostics,
    )


def normalize_prompt(text: str) -> str:
    return preprocess_prompt(text).normalized_prompt


def extract_measurements(text: str) -> list[Measurement]:
    return _extract_measurements(text)


def normalize_units(text: str) -> str:
    return _normalize_units(text)


def extract_quantity_phrases(text: str) -> list[QuantityPhrase]:
    """Extract simple count+noun phrases after deterministic number conversion."""

    numeric = normalize_number_words(text).lower()
    quantities: list[QuantityPhrase] = []
    for match in re.finditer(r"\b(\d+)\s+([a-z][a-z-]*)\b", numeric):
        noun = match.group(2)
        if noun in _UNIT_WORDS or noun == "mm":
            continue
        quantities.append(QuantityPhrase(quantity=int(match.group(1)), noun=noun))
    return quantities


def clean_engineering_text(text: str) -> str:
    """Canonicalize common CAD wording without selecting or executing a tool."""

    cleaned = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", text.lower())
    replacements = (
        (r"\bhollow\s+pipe\b", "hollow tube"),
        (r"\bpipe\b", "tube"),
        (r"\boutside\s+diameter\b", "outer diameter"),
        (r"\bdiameter\s+outside\b", "outer diameter"),
        (r"\bacross\s+outside\b", "outer diameter"),
        (r"\binside\s+diameter\b", "inner diameter"),
        (r"\bbore\b", "inner diameter"),
    )
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned)
    for pattern in _FILLER_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)

    dimension_rewrites = (
        (r"\b(\d+(?:\.\d+)?\s+mm)\s+long\b", r"length \1"),
        (r"\b(\d+(?:\.\d+)?\s+mm)\s+(?:tall|high)\b", r"height \1"),
        (r"\b(\d+(?:\.\d+)?\s+mm)\s+wide\b", r"diameter \1"),
        (r"\b(\d+(?:\.\d+)?\s+mm)\s+in\s+diameter\b", r"diameter \1"),
        (
            r"(?<!outer diameter )(?<!inner diameter )\b(\d+(?:\.\d+)?\s+mm)\s+"
            r"(outer diameter|inner diameter)\b",
            r"\2 \1",
        ),
    )
    for pattern, replacement in dimension_rewrites:
        cleaned = re.sub(pattern, replacement, cleaned)

    cleaned = re.sub(r"[^a-z0-9_.\s-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


@lru_cache(maxsize=1)
def _load_spacy_pipeline() -> tuple[Any | None, str, tuple[str, ...]]:
    try:
        import spacy
    except (ImportError, OSError) as exc:
        return None, "deterministic_fallback", (f"spaCy unavailable: {exc}",)

    try:
        return spacy.load("en_core_web_sm"), "spacy_en_core_web_sm", ()
    except (OSError, IOError) as exc:
        try:
            return spacy.blank("en"), "spacy_blank_en", (
                f"en_core_web_sm unavailable; using blank English tokenizer: {exc}",
            )
        except Exception as blank_exc:  # pragma: no cover - defensive environment fallback
            return None, "deterministic_fallback", (f"spaCy initialization failed: {blank_exc}",)


def _linguistic_normalize(text: str) -> tuple[str, str, list[str]]:
    pipeline, engine, diagnostic_items = _load_spacy_pipeline()
    if pipeline is None:
        fallback = _join_linguistic_tokens(
            re.findall(r"\d+(?:\.\d+)?|[A-Za-z]+(?:'[A-Za-z]+)?|[^\w\s]", text)
        )
        return fallback, engine, list(diagnostic_items)

    doc = pipeline(text)
    tokens: list[str] = []
    for token in doc:
        if token.is_space:
            continue
        lemma = token.lemma_.strip() if token.lemma_ else ""
        if token.pos_ in {"VERB", "AUX"} and lemma and lemma != "-PRON-":
            tokens.append(lemma)
        else:
            tokens.append(token.text)
    return _join_linguistic_tokens(tokens), engine, list(diagnostic_items)


def _join_linguistic_tokens(tokens: list[str]) -> str:
    text = " ".join(tokens)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"(?<=\w)\.\s+(?=\w)", ".", text)
    text = re.sub(r"(?<!\w)-\s+(?=\d)", "-", text)
    return text
