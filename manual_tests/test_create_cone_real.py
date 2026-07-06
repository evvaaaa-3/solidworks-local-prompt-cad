"""Manual real SolidWorks cone creation test."""

from __future__ import annotations

from cad_tools.primitives import create_cone


if __name__ == "__main__":
    print("WARNING: This opens/controls SolidWorks and creates a local .SLDPRT file.")
    result = create_cone(base_diameter_mm=50, height_mm=80, dry_run=False)
    print(result)
    print(f"Output file: {result.get('filepath')}")
