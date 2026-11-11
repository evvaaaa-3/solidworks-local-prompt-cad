from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from utils.output_paths import OUTPUT_ROOT_ENV_VAR


try:
    from fastapi.testclient import TestClient
    from api.main import app
except ImportError:
    TestClient = None
    app = None


@unittest.skipIf(TestClient is None, "FastAPI dependencies are not installed")
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "prompt-to-cad-api"},
        )

    def test_status_does_not_connect_to_solidworks(self) -> None:
        with patch("cad_tools.primitives.connect_solidworks") as connect:
            response = self.client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["default_mode"], "dry_run")
        connect.assert_not_called()

    def test_parse_sphere(self) -> None:
        response = self.client.post(
            "/api/parse",
            json={"prompt": "create sphere diameter 50 mm"},
        )

        self.assertTrue(response.json()["success"])
        self.assertEqual(
            response.json()["validated_intent"]["tool_name"],
            "create_sphere",
        )
        self.assertEqual(response.json()["parser_used"], "rule")
        self.assertEqual(response.json()["validation_status"], "valid")

    def test_parse_accepts_auto_mode(self) -> None:
        response = self.client.post(
            "/api/parse",
            json={"prompt": "create a 50 mm cube", "parser_mode": "auto"},
        )

        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["parser_used"], "rule")

    def test_parse_ambiguous_shaft_returns_clarification_metadata(self) -> None:
        response = self.client.post(
            "/api/parse",
            json={"prompt": "create a shaft"},
        )

        body = response.json()
        self.assertFalse(body["success"])
        self.assertTrue(body["clarification_required"])
        self.assertEqual(body["validation_status"], "missing_dimension")

    def test_ollama_status_endpoint_does_not_connect_to_solidworks(self) -> None:
        with patch("llm.ollama_client.requests.get", side_effect=Exception("down")), \
             patch("cad_tools.primitives.connect_solidworks") as connect:
            response = self.client.get("/api/ollama/status")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["available"])
        connect.assert_not_called()

    def test_negative_dimension_returns_friendly_error(self) -> None:
        response = self.client.post(
            "/api/parse",
            json={"prompt": "create a -50 mm cube"},
        )

        body = response.json()

        self.assertFalse(body["success"])
        self.assertIn("greater than 0", body["error"])

    def test_dry_run_execute_does_not_connect_to_solidworks(self) -> None:
        with patch("cad_tools.primitives.connect_solidworks") as connect:
            response = self.client.post(
                "/api/execute",
                json={
                    "prompt": "create a 50 mm cube",
                    "mode": "dry_run",
                    "confirmed": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["result"]["status"], "dry_run_success")
        connect.assert_not_called()

    def test_real_mode_without_confirmation_is_rejected(self) -> None:
        response = self.client.post(
            "/api/execute",
            json={
                "prompt": "create a 50 mm cube",
                "mode": "real",
                "confirmed": False,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("confirmation", response.json()["error"].lower())

    def test_output_listing_only_returns_known_output_categories(self) -> None:
        response = self.client.get("/api/outputs")

        self.assertEqual(response.status_code, 200)

        allowed_categories = {"parts", "exports", "assemblies"}

        for item in response.json():
            self.assertIn(item["category"], allowed_categories)
            self.assertIn("filename", item)
            self.assertIn("relative_path", item)

            # The API should expose safe app-relative output paths only,
            # not arbitrary absolute filesystem paths.
            relative_path = Path(item["relative_path"])
            self.assertFalse(relative_path.is_absolute())
            self.assertNotIn("..", relative_path.parts)

    def test_output_download_rejects_unknown_category(self) -> None:
        response = self.client.get("/api/outputs/private/README.md")

        self.assertEqual(response.status_code, 404)

    def test_output_listing_includes_assemblies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assembly_dir = Path(temp_dir) / "Assemblies"
            assembly_dir.mkdir(parents=True)
            (assembly_dir / "demo.SLDASM").write_text("assembly", encoding="utf-8")

            with patch.dict("os.environ", {OUTPUT_ROOT_ENV_VAR: temp_dir}, clear=False):
                response = self.client.get("/api/outputs")

        self.assertEqual(response.status_code, 200)

        assemblies = [
            item for item in response.json() if item["category"] == "assemblies"
        ]

        self.assertTrue(
            any(item["filename"] == "demo.SLDASM" for item in assemblies)
        )


if __name__ == "__main__":
    unittest.main()
