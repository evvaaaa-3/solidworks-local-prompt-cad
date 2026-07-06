"""Manual real SolidWorks sphere creation test."""

from __future__ import annotations

from cad_tools.primitives import create_sphere


if __name__ == "__main__":
    print("WARNING: This opens/controls SolidWorks and creates a local .SLDPRT file.")
    result = create_sphere(diameter_mm=50, dry_run=False)
    print(result)
    print(f"Output file: {result.get('filepath')}")
