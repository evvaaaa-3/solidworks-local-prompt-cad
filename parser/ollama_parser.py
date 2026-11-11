"""Compatibility wrapper for the Ollama-backed parser."""

from __future__ import annotations

from llm.intent_parser import parse_prompt_ollama


def parse_with_ollama(prompt: str) -> dict:
    result = parse_prompt_ollama(prompt)
    if not result.success or result.intent is None:
        raise ValueError(result.message or result.code or "Ollama parsing failed.")
    return result.intent
