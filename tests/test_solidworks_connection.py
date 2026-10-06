from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from solidworks_api.connection import connect_solidworks


class SolidWorksConnectionTests(unittest.TestCase):
    def test_connect_uses_active_object_first(self) -> None:
        app = FakeSolidWorksApp()
        client = FakeWin32Client(active_app=app)

        with _fake_win32com(client):
            result = connect_solidworks(visible=True)

        self.assertIs(result, app)
        self.assertEqual(client.calls, ["GetActiveObject"])
        self.assertTrue(app.Visible)

    def test_connect_dispatches_when_no_active_object_exists(self) -> None:
        app = FakeSolidWorksApp()
        client = FakeWin32Client(active_error=RuntimeError("not running"), dispatch_app=app)

        with _fake_win32com(client), patch("solidworks_api.connection.time.sleep"):
            result = connect_solidworks(
                visible=True,
                startup_timeout_seconds=0.1,
                retry_interval_seconds=0.01,
            )

        self.assertIs(result, app)
        self.assertEqual(client.calls, ["GetActiveObject", "Dispatch"])
        self.assertTrue(app.Visible)

    def test_connect_reports_dispatch_failure(self) -> None:
        client = FakeWin32Client(
            active_error=RuntimeError("not running"),
            dispatch_error=RuntimeError("cannot launch"),
        )

        with _fake_win32com(client):
            with self.assertRaisesRegex(RuntimeError, "Could not connect to SolidWorks"):
                connect_solidworks()


class FakeSolidWorksApp:
    def __init__(self) -> None:
        self.Visible = False


class FakeWin32Client:
    def __init__(
        self,
        *,
        active_app: FakeSolidWorksApp | None = None,
        dispatch_app: FakeSolidWorksApp | None = None,
        active_error: Exception | None = None,
        dispatch_error: Exception | None = None,
    ) -> None:
        self.active_app = active_app
        self.dispatch_app = dispatch_app
        self.active_error = active_error
        self.dispatch_error = dispatch_error
        self.calls: list[str] = []

    def GetActiveObject(self, prog_id: str):
        self.calls.append("GetActiveObject")
        self._assert_prog_id(prog_id)
        if self.active_error is not None:
            raise self.active_error
        return self.active_app

    def Dispatch(self, prog_id: str):
        self.calls.append("Dispatch")
        self._assert_prog_id(prog_id)
        if self.dispatch_error is not None:
            raise self.dispatch_error
        return self.dispatch_app

    def _assert_prog_id(self, prog_id: str) -> None:
        if prog_id != "SldWorks.Application":
            raise AssertionError(f"Unexpected ProgID: {prog_id}")


class _fake_win32com:
    def __init__(self, client: FakeWin32Client) -> None:
        self.client = client
        self.original_win32com = sys.modules.get("win32com")
        self.original_client = sys.modules.get("win32com.client")

    def __enter__(self):
        package = types.ModuleType("win32com")
        client_module = types.ModuleType("win32com.client")
        client_module.GetActiveObject = self.client.GetActiveObject  # type: ignore[attr-defined]
        client_module.Dispatch = self.client.Dispatch  # type: ignore[attr-defined]
        package.client = client_module  # type: ignore[attr-defined]
        sys.modules["win32com"] = package
        sys.modules["win32com.client"] = client_module
        return self

    def __exit__(self, *_args):
        if self.original_win32com is None:
            sys.modules.pop("win32com", None)
        else:
            sys.modules["win32com"] = self.original_win32com
        if self.original_client is None:
            sys.modules.pop("win32com.client", None)
        else:
            sys.modules["win32com.client"] = self.original_client


if __name__ == "__main__":
    unittest.main()
