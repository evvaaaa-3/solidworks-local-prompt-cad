"""Manual Front Plane selection debug test.

Run directly only on a Windows machine with SolidWorks installed:

    python manual_tests/test_front_plane_selection.py

This file is intentionally outside tests/ so normal pytest runs do not open
SolidWorks or make COM calls.
"""

from __future__ import annotations

from solidworks_api.connection import connect_solidworks, get_active_doc
from solidworks_api.document import create_new_part, safe_get_title
from solidworks_api.sketch import select_front_plane


def main() -> None:
    sw_app = connect_solidworks(visible=True)
    print("Connected to SolidWorks.")

    try:
        model = get_active_doc(sw_app)
        print("Using existing ActiveDoc.")
    except RuntimeError:
        print("No ActiveDoc found; creating a new part.")
        model = create_new_part(sw_app)

    print(f"ActiveDoc object type: {type(model)}")
    print(f"ActiveDoc title: {safe_get_title(model)}")

    if select_front_plane(model):
        print("Front Plane selection succeeded.")
    else:
        print("Front Plane selection returned False.")


if __name__ == "__main__":
    main()
