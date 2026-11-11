"""Project configuration and filesystem paths."""

from __future__ import annotations

import re
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - requirements install provides it
    def load_dotenv(*_args: object, **_kwargs: object) -> bool:
        return False

from utils.output_paths import (
    get_assemblies_output_dir,
    get_exports_output_dir,
    get_parts_output_dir,
    get_user_output_root,
)


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

OUTPUTS_DIR = get_user_output_root()
PARTS_DIR = get_parts_output_dir()
EXPORTS_DIR = get_exports_output_dir()
ASSEMBLIES_DIR = get_assemblies_output_dir()

BASE_DIR = PROJECT_ROOT
OUTPUT_DIR = OUTPUTS_DIR

DEFAULT_TEMPLATE_PATH = None

DEFAULT_SOLIDWORKS_YEAR = 2022
USER_UNIT = "mm"
SOLIDWORKS_UNIT = "m"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_EXECUTABLE = os.getenv("OLLAMA_EXECUTABLE", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))

MAX_DIMENSION_MM = 10000
MIN_DIMENSION_MM = 0.1
_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9_. -]+")


def mm_to_m(value_mm: float) -> float:
    return value_mm / 1000.0


def sanitize_filename(filename: str, default: str = "output") -> str:
    sanitized = _SAFE_FILENAME_PATTERN.sub("_", filename.strip())
    sanitized = sanitized.replace("..", "_")
    sanitized = sanitized.replace("/", "_").replace("\\", "_").replace(":", "_")
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = sanitized.strip(" .")
    return sanitized or default


def ensure_unique_filepath(filepath: str | Path) -> Path:
    path = Path(filepath)
    if not path.exists():
        return path

    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
