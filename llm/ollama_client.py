"""Small, local-only Ollama HTTP client."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import threading
import time
from typing import Any

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - exercised by environments without requirements installed
    requests = None  # type: ignore[assignment]

from config import OLLAMA_BASE_URL, OLLAMA_EXECUTABLE, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS


class OllamaError(RuntimeError):
    """Raised for structured Ollama failures."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class OllamaStatus:
    available: bool
    model: str
    model_available: bool
    base_url: str
    error: str | None = None


class OllamaClient:
    """HTTP client for a local Ollama server. No cloud fallback is used."""

    _startup_lock = threading.Lock()
    _server_process: subprocess.Popen[Any] | None = None

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str | None = None,
        timeout_seconds: float = OLLAMA_TIMEOUT_SECONDS,
        executable_path: str = OLLAMA_EXECUTABLE,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model if model is not None else OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds
        self.executable_path = executable_path

    def status(self) -> OllamaStatus:
        try:
            models = self.list_models()
        except OllamaError as exc:
            return OllamaStatus(False, self.model, False, self.base_url, str(exc))
        except Exception as exc:
            return OllamaStatus(
                False,
                self.model,
                False,
                self.base_url,
                f"Unexpected Ollama health-check failure: {exc}",
            )
        model_available = bool(self.model) and any(_model_matches(self.model, item) for item in models)
        return OllamaStatus(True, self.model, model_available, self.base_url, None)

    def list_models(self) -> set[str]:
        try:
            return self._list_models_once()
        except OllamaError as initial_error:
            self._start_server_if_needed(initial_error)
            return self._list_models_once()

    def _list_models_once(self) -> set[str]:
        if requests is None:
            raise OllamaError("ollama_unavailable", "The requests package is not installed.")
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=min(self.timeout_seconds, 2.0),
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise OllamaError("ollama_unavailable", "Ollama health check timed out.") from exc
        except requests.RequestException as exc:
            raise OllamaError("ollama_unavailable", f"Ollama is unavailable: {exc}") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise OllamaError("ollama_unavailable", "Ollama health check returned invalid JSON.") from exc
        return {item.get("name", "") for item in data.get("models", []) if item.get("name")}

    def _start_server_if_needed(self, initial_error: OllamaError) -> None:
        executable = Path(self.executable_path).expanduser() if self.executable_path else None
        if executable is None or not executable.is_file():
            configured = str(executable) if executable is not None else "<not configured>"
            raise OllamaError(
                "ollama_unavailable",
                f"Ollama API is unavailable and OLLAMA_EXECUTABLE was not found: {configured}",
            ) from initial_error

        with self._startup_lock:
            try:
                self._list_models_once()
                return
            except OllamaError:
                pass

            process = type(self)._server_process
            if process is None or process.poll() is not None:
                try:
                    type(self)._server_process = subprocess.Popen(
                        [str(executable), "serve"],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        startupinfo=_hidden_startup_info(),
                    )
                except OSError as exc:
                    raise OllamaError(
                        "ollama_unavailable",
                        f"Ollama could not be started from {executable}: {exc}",
                    ) from exc

            deadline = time.monotonic() + self.timeout_seconds
            last_error: OllamaError | None = None
            while time.monotonic() < deadline:
                try:
                    self._list_models_once()
                    return
                except OllamaError as exc:
                    last_error = exc
                    time.sleep(0.25)

            raise OllamaError(
                "ollama_unavailable",
                f"Ollama did not become available within {self.timeout_seconds:g} seconds: "
                f"{last_error or initial_error}",
            )

    def ensure_ready(self) -> None:
        status = self.status()
        if not status.available:
            raise OllamaError("ollama_unavailable", status.error or "Ollama is unavailable.")
        if not self.model:
            raise OllamaError("model_not_found", "OLLAMA_MODEL is not configured.")
        if not status.model_available:
            raise OllamaError("model_not_found", f"Ollama model is not installed: {self.model}")

    def generate_json(self, prompt: str, system_prompt: str) -> str:
        if requests is None:
            raise OllamaError("ollama_unavailable", "The requests package is not installed.")
        self.ensure_ready()
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise OllamaError("timeout", "Ollama generation timed out.") from exc
        except requests.RequestException as exc:
            raise OllamaError("ollama_unavailable", f"Ollama generation failed: {exc}") from exc
        data = response.json()
        text = data.get("response")
        if not isinstance(text, str):
            raise OllamaError("invalid_json", "Ollama response did not contain text.")
        return text


def _model_matches(configured: str, installed: str) -> bool:
    return configured == installed or configured.split(":", 1)[0] == installed.split(":", 1)[0]


def _hidden_startup_info() -> Any | None:
    startup_info_type = getattr(subprocess, "STARTUPINFO", None)
    if startup_info_type is None:
        return None
    startup_info = startup_info_type()
    startup_info.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
    startup_info.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
    return startup_info
