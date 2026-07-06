"""Manual SolidWorks sphere sketch profile inspection test.

Run directly only on a Windows machine with SolidWorks installed:

    python manual_tests/test_sphere_profile_only.py

This creates a new part, draws the closed sphere revolve profile, and stops in
the sketch so the arc, diameter edge, and construction centerline can be
inspected before a revolve feature is attempted.
"""

from __future__ import annotations

from config import mm_to_m
from solidworks_api.connection import connect_solidworks
from solidworks_api.document import create_new_part
from solidworks_api.sketch import (
    draw_closed_sphere_revolve_profile,
    select_front_plane,
    start_sketch,
)


def main() -> None:
    print("WARNING: This opens/controls SolidWorks and creates a sketch for inspection.")
    sw_app = connect_solidworks(visible=True)
    model = create_new_part(sw_app)
    select_front_plane(model)
    start_sketch(model)
    result = draw_closed_sphere_revolve_profile(model, mm_to_m(25))
    print("Sphere profile sketch created. Inspect the active sketch in SolidWorks.")
    print(result)


if __name__ == "__main__":
    main()
