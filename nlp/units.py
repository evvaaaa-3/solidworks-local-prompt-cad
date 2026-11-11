"""Deterministic number-word and CAD unit normalization."""

from __future__ import annotations

from dataclasses import dataclass
import re


_SMALL_NUMBERS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_NUMBER_WORDS = set(_SMALL_NUMBERS) | set(_TENS) | {"hundred", "thousand", "and"}
_TOKEN_PATTERN = re.compile(r"-?\d+(?:\.\d+)?|[A-Za-z]+(?:-[A-Za-z]+)?|[^\w\s]")

_UNIT_FACTORS = {
    "mm": 1.0,
    "millimeter": 1.0,
    "millimeters": 1.0,
    "millimetre": 1.0,
    "millimetres": 1.0,
    "cm": 10.0,
    "centimeter": 10.0,
    "centimeters": 10.0,
    "centimetre": 10.0,
    "centimetres": 10.0,
    "m": 1000.0,
    "meter": 1000.0,
    "meters": 1000.0,
    "metre": 1000.0,
    "metres": 1000.0,
}
_UNIT_PATTERN = re.compile(
    r"(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>"
    + "|".join(sorted((re.escape(unit) for unit in _UNIT_FACTORS), key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Measurement:
    original_text: str
    value: float
    unit: str
    value_mm: float


def normalize_number_words(text: str) -> str:
    """Convert common written number phrases to digits without model inference."""

    tokens = _TOKEN_PATTERN.findall(text)
    normalized: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        lowered = token.lower()
        if lowered not in _NUMBER_WORDS or lowered == "and":
            normalized.append(token)
            index += 1
            continue
        words: list[str] = []
        cursor = index
        while cursor < len(tokens):
            candidate = tokens[cursor].lower()
            if candidate not in _NUMBER_WORDS:
                break
            words.append(candidate)
            cursor += 1
        while words and words[-1] == "and":
            words.pop()
            cursor -= 1
        if not words:
            normalized.append(token)
            index += 1
            continue
        normalized.append(_format_number(float(_parse_number_words(words))))
        index = cursor
    return _join_tokens(normalized)


def extract_measurements(text: str) -> list[Measurement]:
    """Extract explicit measurements and convert them to millimetres."""

    numeric_text = normalize_number_words(text)
    measurements: list[Measurement] = []
    for match in _UNIT_PATTERN.finditer(numeric_text):
        value = float(match.group("value"))
        unit = match.group("unit").lower()
        measurements.append(
            Measurement(
                original_text=match.group(0),
                value=value,
                unit=unit,
                value_mm=value * _UNIT_FACTORS[unit],
            )
        )
    return measurements


def normalize_units(text: str) -> str:
    """Convert supported length units to canonical millimetre expressions."""

    numeric_text = normalize_number_words(text)

    def replace(match: re.Match[str]) -> str:
        value = float(match.group("value"))
        factor = _UNIT_FACTORS[match.group("unit").lower()]
        return f"{_format_number(value * factor)} mm"

    return _UNIT_PATTERN.sub(replace, numeric_text)


def _parse_number_words(words: list[str]) -> int:
    total = 0
    current = 0
    for word in words:
        if word == "and":
            continue
        if word in _SMALL_NUMBERS:
            current += _SMALL_NUMBERS[word]
        elif word in _TENS:
            current += _TENS[word]
        elif word == "hundred":
            current = max(1, current) * 100
        elif word == "thousand":
            total += max(1, current) * 1000
            current = 0
    return total + current


def _format_number(value: float) -> str:
    return f"{value:g}"


def _join_tokens(tokens: list[str]) -> str:
    text = " ".join(tokens)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"(?<=\w)\.\s+(?=\w)", ".", text)
    text = re.sub(r"([({])\s+", r"\1", text)
    text = re.sub(r"\s+([)}])", r"\1", text)
    return text
