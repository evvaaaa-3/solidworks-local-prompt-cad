from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from config import ensure_unique_filepath, mm_to_m, sanitize_filename


class ConfigTests(unittest.TestCase):
    def test_mm_to_m_conversion(self) -> None:
        self.assertEqual(mm_to_m(1000), 1.0)
        self.assertEqual(mm_to_m(50), 0.05)

    def test_sanitize_filename_removes_unsafe_path_parts(self) -> None:
        self.assertEqual(sanitize_filename("..\\bad:name.step"), "_bad_name.step")

    def test_ensure_unique_filepath_adds_increment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "cube.SLDPRT"
            existing.write_text("already here")

            unique = ensure_unique_filepath(existing)

            self.assertEqual(unique.name, "cube_1.SLDPRT")
