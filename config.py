"""Project configuration and filesystem paths."""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PARTS_DIR = OUTPUTS_DIR / "parts"
EXPORTS_DIR = OUTPUTS_DIR / "exports"

BASE_DIR = PROJECT_ROOT
OUTPUT_DIR = OUTPUTS_DIR

DEFAULT_TEMPLATE_PATH = None

DEFAULT_SOLIDWORKS_YEAR = 2022
USER_UNIT = "mm"
SOLIDWORKS_UNIT = "m"

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


for directory in (OUTPUTS_DIR, PARTS_DIR, EXPORTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)
