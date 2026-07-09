from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from solidworks_api.document import save_part
from solidworks_api.export import export_step
from utils.output_paths import (
    OUTPUT_ROOT_ENV_VAR,
    ensure_output_dirs,
    get_exports_output_dir,
    get_parts_output_dir,
    get_user_output_root,
    is_safe_output_path,
)


class FakeSaveModel:
    def __init__(self, write_file: bool) -> None:
        self.write_file = write_file

    def SaveAs(self, filepath: str) -> bool:
        if self.write_file:
            Path(filepath).write_text("saved", encoding="utf-8")
        return True


class OutputPathTests(unittest.TestCase):
    def test_default_output_root_is_under_documents(self) -> None:
        with patch.dict("os.environ", {OUTPUT_ROOT_ENV_VAR: ""}, clear=False):
            expected = Path.home() / "Documents" / "MCP SolidWorks" / "Outputs"
            self.assertEqual(get_user_output_root(), expected.resolve())

    def test_environment_override_sets_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict("os.environ", {OUTPUT_ROOT_ENV_VAR: temp_dir}, clear=False):
                self.assertEqual(get_user_output_root(), Path(temp_dir).resolve())

    def test_ensure_output_dirs_creates_parts_and_exports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict("os.environ", {OUTPUT_ROOT_ENV_VAR: temp_dir}, clear=False):
                root, parts, exports = ensure_output_dirs()

                self.assertTrue(root.is_dir())
                self.assertTrue(parts.is_dir())
                self.assertTrue(exports.is_dir())
                self.assertEqual(parts, get_parts_output_dir())
                self.assertEqual(exports, get_exports_output_dir())

    def test_safe_output_path_accepts_files_inside_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict("os.environ", {OUTPUT_ROOT_ENV_VAR: temp_dir}, clear=False):
                inside = get_parts_output_dir() / "sphere.SLDPRT"

                self.assertTrue(is_safe_output_path(inside))

    def test_safe_output_path_rejects_path_traversal_and_outside_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with tempfile.TemporaryDirectory() as outside_dir:
                with patch.dict("os.environ", {OUTPUT_ROOT_ENV_VAR: temp_dir}, clear=False):
                    traversal = get_user_output_root() / ".." / "outside.SLDPRT"
                    outside = Path(outside_dir) / "outside.SLDPRT"

                    self.assertFalse(is_safe_output_path(traversal))
                    self.assertFalse(is_safe_output_path(outside))

    def test_save_part_requires_file_to_exist_after_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "missing.SLDPRT"

            with self.assertRaisesRegex(RuntimeError, "file was not saved successfully"):
                save_part(FakeSaveModel(write_file=False), str(target))

    def test_save_part_returns_success_when_file_exists_after_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "saved.SLDPRT"

            result = save_part(FakeSaveModel(write_file=True), str(target))

            self.assertEqual(result["status"], "success")
            self.assertTrue(Path(result["filepath"]).exists())

    def test_export_step_requires_file_to_exist_after_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "missing.step"

            with self.assertRaisesRegex(RuntimeError, "file was not saved successfully"):
                export_step(FakeSaveModel(write_file=False), str(target))


if __name__ == "__main__":
    unittest.main()
