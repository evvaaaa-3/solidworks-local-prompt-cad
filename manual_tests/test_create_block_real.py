"""Manual real SolidWorks block creation test."""

from __future__ import annotations

from cad_tools.primitives import create_block


if __name__ == "__main__":
    print("This manual test opens/controls SolidWorks and creates a local .SLDPRT file.")
    print(create_block(length_mm=100, width_mm=60, height_mm=20, dry_run=False))
