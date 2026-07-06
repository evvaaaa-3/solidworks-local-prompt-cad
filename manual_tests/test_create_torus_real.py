"""Manual real SolidWorks torus creation test."""

from __future__ import annotations

from cad_tools.primitives import create_torus


if __name__ == "__main__":
    print("WARNING: This opens/controls SolidWorks and creates a local .SLDPRT file.")
    print("Torus revolve behavior can vary by SolidWorks COM state; failures are diagnostic.")
    result = create_torus(major_diameter_mm=80, minor_diameter_mm=20, dry_run=False)
    print(result)
    print(f"Output file: {result.get('filepath')}")
