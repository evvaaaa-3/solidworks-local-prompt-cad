from __future__ import annotations

import unittest

from solidworks_api.document import create_new_part, safe_get_doc_type


class FakePartDocument:
    def GetTitle(self) -> str:
        return "Part1"

    def GetType(self) -> int:
        return 1


class FakePartDocumentWithPropertyType:
    GetType = 1

    def GetTitle(self) -> str:
        return "PartPropertyType"


class FakeSolidWorksApp:
    def __init__(self) -> None:
        self.ActiveDoc = FakePartDocument()
        self.new_part_called = False

    def GetUserPreferenceStringValue(self, preference_id: int) -> str:
        return ""

    def NewPart(self):
        self.new_part_called = True
        return None


class DocumentTests(unittest.TestCase):
    def test_create_new_part_falls_back_to_active_doc_when_new_part_returns_none(self) -> None:
        sw_app = FakeSolidWorksApp()

        model = create_new_part(sw_app)

        self.assertTrue(sw_app.new_part_called)
        self.assertIs(model, sw_app.ActiveDoc)
        self.assertEqual(model.GetTitle(), "Part1")

    def test_safe_get_doc_type_handles_property_form(self) -> None:
        self.assertEqual(safe_get_doc_type(FakePartDocumentWithPropertyType()), 1)


if __name__ == "__main__":
    unittest.main()
