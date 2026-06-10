"""Placeholder for the future Ollama-backed parser.

Stage 1 must not call Ollama. This module exists only to reserve the future
integration point.

Later stages will run Ollama locally. Ollama will only return structured JSON
intent and will never generate or execute SolidWorks code.
"""

from __future__ import annotations


def parse_with_ollama(prompt: str) -> dict:
    raise NotImplementedError("Ollama parser will be implemented in a later stage.")
