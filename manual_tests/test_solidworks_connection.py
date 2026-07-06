"""Manual SolidWorks connection smoke test.

Run directly only on a Windows machine with SolidWorks installed:

    python manual_tests/test_solidworks_connection.py

This file is intentionally outside tests/ so normal pytest runs do not open
SolidWorks or make COM calls.
"""

from __future__ import annotations

from solidworks_api.connection import connect_solidworks, get_active_doc
from solidworks_api.document import create_new_part


def main() -> None:
    sw_app = connect_solidworks(visible=True)
    print("Connected to SolidWorks.")

    model = create_new_part(sw_app)
    if model is None:
        raise RuntimeError("create_new_part did not return a model.")
    print("create_new_part returned a model.")

    try:
        active_model = get_active_doc(sw_app)
    except RuntimeError as exc:
        print(f"No active document: {exc}")
    else:
        print(f"ActiveDoc title: {active_model.GetTitle()}")


if __name__ == "__main__":
    main()
