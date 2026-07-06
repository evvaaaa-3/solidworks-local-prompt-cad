from __future__ import annotations

import unittest
from unittest.mock import patch

from app import _mode_label, handle_command


class AppCliTests(unittest.TestCase):
    def test_mode_label_defaults_to_dry_run(self) -> None:
        self.assertEqual(_mode_label(True), "DRY-RUN")

    def test_dry_command_switches_to_dry_run(self) -> None:
        dry_run, should_exit = handle_command("dry", dry_run=False)

        self.assertTrue(dry_run)
        self.assertFalse(should_exit)

    def test_real_command_requires_confirmation(self) -> None:
        with patch("builtins.input", return_value="n"):
            dry_run, should_exit = handle_command("real", dry_run=True)

        self.assertTrue(dry_run)
        self.assertFalse(should_exit)

    def test_real_command_switches_when_confirmed(self) -> None:
        with patch("builtins.input", return_value="y"):
            dry_run, should_exit = handle_command("solidworks", dry_run=True)

        self.assertFalse(dry_run)
        self.assertFalse(should_exit)

    def test_exit_command_exits(self) -> None:
        dry_run, should_exit = handle_command("exit", dry_run=True)

        self.assertTrue(dry_run)
        self.assertTrue(should_exit)


if __name__ == "__main__":
    unittest.main()
