"""Project configuration and filesystem paths."""

from __future__ import annotations

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


def mm_to_m(value_mm: float) -> float:
    return value_mm / 1000.0


for directory in (OUTPUTS_DIR, PARTS_DIR, EXPORTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)
