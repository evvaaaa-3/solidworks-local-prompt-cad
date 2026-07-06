"""Manual real SolidWorks test for Stage 2A extruded primitives.

Run only on a Windows machine with SolidWorks installed. This opens/controls
SolidWorks and creates local .SLDPRT files under outputs/parts/.
"""

from __future__ import annotations

from cad_tools.primitives import (
    create_block,
    create_cube,
    create_cylinder,
    create_disc,
    create_plate,
    create_plate_with_hole,
    create_tube,
)


def main() -> None:
    print("WARNING: This test opens/controls SolidWorks and creates local files.")
    tools = [
        lambda: create_cube(side_mm=50, dry_run=False),
        lambda: create_block(length_mm=100, width_mm=60, height_mm=20, dry_run=False),
        lambda: create_cylinder(diameter_mm=30, height_mm=80, dry_run=False),
        lambda: create_disc(diameter_mm=50, thickness_mm=5, dry_run=False),
        lambda: create_plate(length_mm=100, width_mm=60, thickness_mm=5, dry_run=False),
        lambda: create_tube(
            outer_diameter_mm=50,
            inner_diameter_mm=30,
            height_mm=80,
            dry_run=False,
        ),
        lambda: create_plate_with_hole(
            length_mm=100,
            width_mm=60,
            thickness_mm=5,
            hole_diameter_mm=20,
            dry_run=False,
        ),
    ]
    for run_tool in tools:
        print(run_tool())


if __name__ == "__main__":
    main()
