"""Manual SolidWorks connection smoke test.

Run directly only on a Windows machine with SolidWorks installed:

    python manual_tests/test_solidworks_connection.py

This file is intentionally outside tests/ so normal pytest runs do not open
SolidWorks or make COM calls.
"""

from __future__ import annotations

from solidworks_api.connection import connect_solidworks, get_active_doc


def main() -> None:
    sw_app = connect_solidworks(visible=True)
    print("Connected to SolidWorks.")
    try:
        model = get_active_doc(sw_app)
    except RuntimeError as exc:
        print(f"No active document: {exc}")
    else:
        print(f"Active document: {model.GetTitle()}")


if __name__ == "__main__":
    main()
