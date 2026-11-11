from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from llm.intent_parser import parse_prompt_ollama
from llm.ollama_client import OllamaClient
from llm.response_parser import extract_json_object
from parser.intent_parser import parse_prompt_with_metadata


class FakeRequestException(Exception):
    pass


class FakeTimeout(FakeRequestException):
    pass


def fake_requests(get):
    return SimpleNamespace(
        get=get,
        post=Mock(),
        Timeout=FakeTimeout,
        RequestException=FakeRequestException,
    )


class OllamaParserTests(unittest.TestCase):
    def tearDown(self) -> None:
        OllamaClient._server_process = None

    def test_extracts_fenced_json(self) -> None:
        parsed = extract_json_object('```json\n{"tool_name":"create_cube","parameters":{"side_mm":50}}\n```')

        self.assertEqual(parsed["tool_name"], "create_cube")

    def test_extracts_json_with_leading_and_trailing_text(self) -> None:
        parsed = extract_json_object('Here: {"tool_name":"create_cube","parameters":{"side_mm":50}} done')

        self.assertEqual(parsed["parameters"]["side_mm"], 50)

    def test_malformed_json_raises(self) -> None:
        with self.assertRaises(ValueError):
            extract_json_object("{not-json")

    def test_ollama_status_success_and_model_available(self) -> None:
        response = Mock()
        response.json.return_value = {"models": [{"name": "llama3.1"}]}
        response.raise_for_status.return_value = None

        with patch("llm.ollama_client.requests", fake_requests(Mock(return_value=response))):
            status = OllamaClient(model="llama3.1").status()

        self.assertTrue(status.available)
        self.assertTrue(status.model_available)

    def test_ollama_status_model_missing(self) -> None:
        response = Mock()
        response.json.return_value = {"models": [{"name": "other"}]}
        response.raise_for_status.return_value = None

        with patch("llm.ollama_client.requests", fake_requests(Mock(return_value=response))):
            status = OllamaClient(model="llama3.1").status()

        self.assertTrue(status.available)
        self.assertFalse(status.model_available)

    def test_ollama_model_latest_tag_matches_configured_name(self) -> None:
        response = Mock()
        response.json.return_value = {"models": [{"name": "llama3.2:latest"}]}
        response.raise_for_status.return_value = None

        with patch("llm.ollama_client.requests", fake_requests(Mock(return_value=response))):
            status = OllamaClient(model="llama3.2").status()

        self.assertTrue(status.model_available)

    def test_ollama_status_unavailable(self) -> None:
        with patch("llm.ollama_client.requests", fake_requests(Mock(side_effect=FakeRequestException("down")))):
            status = OllamaClient(model="llama3.1").status()

        self.assertFalse(status.available)

    def test_ollama_starts_hidden_server_and_polls_until_ready(self) -> None:
        response = Mock()
        response.json.return_value = {"models": [{"name": "llama3.2:latest"}]}
        response.raise_for_status.return_value = None
        get = Mock(
            side_effect=[
                FakeRequestException("down"),
                FakeRequestException("still down"),
                response,
                response,
            ]
        )
        process = Mock()
        process.poll.return_value = None

        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "ollama.exe"
            executable.touch()
            with patch("llm.ollama_client.requests", fake_requests(get)), \
                 patch("llm.ollama_client.subprocess.Popen", return_value=process) as popen, \
                 patch("llm.ollama_client.time.sleep"):
                status = OllamaClient(
                    model="llama3.2",
                    executable_path=str(executable),
                    timeout_seconds=1,
                ).status()

        self.assertTrue(status.available)
        self.assertTrue(status.model_available)
        popen.assert_called_once()
        self.assertEqual(popen.call_args.args[0], [str(executable), "serve"])

    def test_ollama_missing_executable_returns_structured_unavailable_error(self) -> None:
        with patch("llm.ollama_client.requests", fake_requests(Mock(side_effect=FakeRequestException("down")))):
            status = OllamaClient(
                model="llama3.2",
                executable_path="C:/missing/ollama.exe",
            ).status()

        self.assertFalse(status.available)
        self.assertIn("OLLAMA_EXECUTABLE was not found", status.error)

    def test_parse_prompt_ollama_successful_json(self) -> None:
        client = Mock()
        client.generate_json.return_value = '{"tool_name":"create_cube","parameters":{"side_mm":50}}'

        result = parse_prompt_ollama("cube", client=client)

        self.assertTrue(result.success)
        self.assertEqual(result.intent["tool_name"], "create_cube")

    def test_ollama_parameter_aliases_are_canonicalized_before_validation(self) -> None:
        client = Mock()
        client.generate_json.return_value = (
            '{"tool_name":"create_tube","parameters":'
            '{"length":80,"outer_diameter":50,"inner_diameter":30}}'
        )

        result = parse_prompt_ollama("hollow tube", client=client)

        self.assertTrue(result.success)
        self.assertEqual(
            result.intent["parameters"],
            {"height_mm": 80, "outer_diameter_mm": 50, "inner_diameter_mm": 30},
        )

    def test_unknown_ollama_parameter_is_still_rejected(self) -> None:
        client = Mock()
        client.generate_json.return_value = (
            '{"tool_name":"create_cube","parameters":{"sideways":50}}'
        )

        result = parse_prompt_ollama("cube", client=client)

        self.assertFalse(result.success)
        self.assertEqual(result.code, "schema_validation_failed")

    def test_parse_prompt_ollama_schema_failure(self) -> None:
        client = Mock()
        client.generate_json.return_value = '{"tool_name":"create_cube","parameters":{"side_mm":-1}}'

        result = parse_prompt_ollama("cube", client=client)

        self.assertFalse(result.success)
        self.assertEqual(result.code, "schema_validation_failed")

    def test_parse_prompt_ollama_clarification(self) -> None:
        client = Mock()
        client.generate_json.return_value = (
            '{"clarification_required":true,"missing_fields":["length_mm"],'
            '"clarification_message":"What length should the shaft be?"}'
        )

        result = parse_prompt_ollama("create a shaft", client=client)

        self.assertFalse(result.success)
        self.assertTrue(result.clarification_required)
        self.assertEqual(result.missing_fields, ["length_mm"])

    def test_rule_mode_does_not_call_ollama(self) -> None:
        with patch("parser.intent_parser.parse_prompt_ollama") as ollama:
            result = parse_prompt_with_metadata("create a 50 mm cube", parser_mode="rule")

        self.assertTrue(result.success)
        self.assertEqual(result.metadata.parser_used, "rule")
        ollama.assert_not_called()
        self.assertEqual(result.metadata.raw_prompt, "create a 50 mm cube")
        self.assertIn("50 mm cube", result.metadata.normalized_prompt)

    def test_ollama_mode_uses_model_output(self) -> None:
        fake = Mock(success=True, intent={"tool_name": "create_cube", "parameters": {"side_mm": 50}})
        with patch("parser.intent_parser.parse_prompt_ollama", return_value=fake):
            result = parse_prompt_with_metadata("cube please", parser_mode="ollama")

        self.assertTrue(result.success)
        self.assertEqual(result.metadata.parser_used, "ollama")

    def test_auto_mode_falls_back_to_ollama_after_rule_failure(self) -> None:
        fake = Mock(success=True, intent={"tool_name": "create_cube", "parameters": {"side_mm": 50}})
        with patch("parser.intent_parser.parse_prompt_ollama", return_value=fake):
            result = parse_prompt_with_metadata("make the small blocky thing", parser_mode="auto")

        self.assertTrue(result.success)
        self.assertEqual(result.metadata.parser_used, "ollama")

    def test_create_shaft_without_dimensions_requires_clarification(self) -> None:
        result = parse_prompt_with_metadata("create a shaft", parser_mode="rule")

        self.assertFalse(result.success)
        self.assertTrue(result.metadata.clarification_required)
        self.assertEqual(result.metadata.error_code, "missing_dimension")

    def test_create_shaft_with_dimensions_parses(self) -> None:
        result = parse_prompt_with_metadata(
            "Create a shaft 100 mm long and 30 mm in diameter",
            parser_mode="rule",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.parsed_intent["tool_name"], "create_shaft")
        self.assertEqual(result.parsed_intent["parameters"]["length_mm"], 100)
        self.assertEqual(result.parsed_intent["parameters"]["diameter_mm"], 30)


if __name__ == "__main__":
    unittest.main()
