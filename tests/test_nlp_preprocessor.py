from __future__ import annotations

import unittest
from unittest.mock import patch

from router import tool_router
from nlp.preprocessor import (
    extract_quantity_phrases,
    normalize_prompt,
    preprocess_prompt,
)


class NLPPreprocessorTests(unittest.TestCase):
    def test_converts_five_centimetres_to_millimetres(self) -> None:
        self.assertEqual(normalize_prompt("5 cm"), "50 mm")

    def test_converts_eight_centimetres_to_millimetres(self) -> None:
        self.assertEqual(normalize_prompt("8 cm"), "80 mm")

    def test_converts_metres_to_millimetres(self) -> None:
        self.assertEqual(normalize_prompt("0.1 m"), "100 mm")

    def test_converts_written_number_and_unit(self) -> None:
        self.assertEqual(normalize_prompt("fifty millimetres"), "50 mm")

    def test_extracts_quantity_phrase(self) -> None:
        quantities = extract_quantity_phrases("two cylinders")

        self.assertEqual(quantities[0].quantity, 2)
        self.assertEqual(quantities[0].noun, "cylinders")

    def test_normalizes_pipe_and_tube_wording(self) -> None:
        normalized = normalize_prompt(
            "Make me a hollow pipe that's 8 cm long, 5 cm across outside and has a 3 cm bore"
        )

        self.assertIn("hollow tube", normalized)
        self.assertIn("length 80 mm", normalized)
        self.assertIn("outer diameter 50 mm", normalized)
        self.assertIn("inner diameter 30 mm", normalized)

    def test_normalizes_written_post_dimensions(self) -> None:
        result = preprocess_prompt(
            "I want two cylindrical posts, each twenty millimetres wide and thirty millimetres tall"
        )

        self.assertIn("2 cylindrical posts", result.normalized_prompt)
        self.assertIn("diameter 20 mm", result.normalized_prompt)
        self.assertIn("height 30 mm", result.normalized_prompt)

    def test_raw_prompt_is_preserved(self) -> None:
        raw = "Give me a fifty millimetre cube"

        result = preprocess_prompt(raw)

        self.assertEqual(result.raw_prompt, raw)
        self.assertIn("50 mm cube", result.normalized_prompt)

    def test_empty_prompt_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            preprocess_prompt("   ")

    def test_preprocessing_does_not_create_tool_names(self) -> None:
        metadata = preprocess_prompt("make a 50 mm cube").metadata()

        self.assertNotIn("tool_name", metadata)
        self.assertNotIn("parameters", metadata)

    def test_preprocessing_never_executes_cad(self) -> None:
        with patch.object(tool_router, "route_intent") as route:
            preprocess_prompt("make a 50 mm cube")

        route.assert_not_called()


if __name__ == "__main__":
    unittest.main()
