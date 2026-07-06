"""Manual real SolidWorks cylinder creation test."""

from __future__ import annotations

from cad_tools.primitives import create_cylinder


if __name__ == "__main__":
    print("This manual test opens/controls SolidWorks and creates a local .SLDPRT file.")
    print(create_cylinder(diameter_mm=30, height_mm=80, dry_run=False))
