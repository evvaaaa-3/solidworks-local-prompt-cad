"""Manual real SolidWorks cube creation test."""

from __future__ import annotations

from cad_tools.primitives import create_cube


if __name__ == "__main__":
    print("This manual test opens/controls SolidWorks and creates a local .SLDPRT file.")
    print(create_cube(side_mm=50, dry_run=False))
