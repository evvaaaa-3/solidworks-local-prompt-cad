"""Local LLM integration package for Ollama-backed CAD intent parsing."""

from llm.intent_parser import parse_prompt_ollama
from llm.ollama_client import OllamaClient, OllamaError, OllamaStatus

__all__ = ["OllamaClient", "OllamaError", "OllamaStatus", "parse_prompt_ollama"]
