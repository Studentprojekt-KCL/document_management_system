"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the gateway Pydantic schemas.
"""

import unittest

from pydantic import ValidationError

from gateway.schemas import (
    ClassificationResult,
    FileMetadata,
    HealthCheck,
    InputItem,
    MetadataTemplate,
    PointerRequest,
    RankResponse,
    SummaryResult,
)

GITLAB_POINTER = "https://gitlab.dms-lookup.com/api/v4/projects/7/repository/files/doc.txt"


# ---------------------------------------------------------------------------
# FileMetadata
# ---------------------------------------------------------------------------


class TestFileMetadata(unittest.TestCase):

    def test_valid_required_fields_only(self) -> None:
        m = FileMetadata(score=0.9, unique_pointer=GITLAB_POINTER)
        self.assertEqual(m.score, 0.9)
        self.assertEqual(m.unique_pointer, GITLAB_POINTER)

    def test_optional_fields_default_to_none(self) -> None:
        m = FileMetadata(score=0.5, unique_pointer=GITLAB_POINTER)
        for field in (
            "name",
            "size",
            "type",
            "source_system",
            "file_type",
            "file_type_description",
            "last_edit_date",
            "clickable_url",
        ):
            self.assertIsNone(getattr(m, field))

    def test_optional_fields_accepted(self) -> None:
        m = FileMetadata(
            score=0.5,
            unique_pointer=GITLAB_POINTER,
            name="doc.txt",
            last_edit_date="2026-01-01",
        )
        self.assertEqual(m.name, "doc.txt")
        self.assertEqual(m.last_edit_date, "2026-01-01")

    def test_extra_fields_are_ignored(self) -> None:
        m = FileMetadata(score=0.5, unique_pointer=GITLAB_POINTER, unknown_field="x")
        self.assertFalse(hasattr(m, "unknown_field"))

    def test_missing_score_raises(self) -> None:
        with self.assertRaises(ValidationError):
            FileMetadata(unique_pointer=GITLAB_POINTER)

    def test_missing_unique_pointer_raises(self) -> None:
        with self.assertRaises(ValidationError):
            FileMetadata(score=0.5)

    def test_strict_str_rejects_int_pointer(self) -> None:
        with self.assertRaises(ValidationError):
            FileMetadata(score=0.5, unique_pointer=123)


# ---------------------------------------------------------------------------
# RankResponse
# ---------------------------------------------------------------------------


class TestRankResponse(unittest.TestCase):

    def test_valid_with_empty_list(self) -> None:
        r = RankResponse(ranked_results=[])
        self.assertEqual(r.ranked_results, [])

    def test_valid_with_file_metadata_items(self) -> None:
        items = [
            FileMetadata(score=0.9, unique_pointer="ptr-1"),
            FileMetadata(score=0.7, unique_pointer="ptr-2"),
        ]
        r = RankResponse(ranked_results=items)
        self.assertEqual(len(r.ranked_results), 2)

    def test_missing_ranked_results_raises(self) -> None:
        with self.assertRaises(ValidationError):
            RankResponse()


# ---------------------------------------------------------------------------
# HealthCheck
# ---------------------------------------------------------------------------


class TestHealthCheck(unittest.TestCase):

    def test_valid(self) -> None:
        h = HealthCheck(status="active", model_loaded=True, device="cuda")
        self.assertEqual(h.status, "active")
        self.assertTrue(h.model_loaded)
        self.assertEqual(h.device, "cuda")

    def test_missing_field_raises(self) -> None:
        with self.assertRaises(ValidationError):
            HealthCheck(status="active", model_loaded=True)  # missing device


# ---------------------------------------------------------------------------
# MetadataTemplate
# ---------------------------------------------------------------------------


class TestMetadataTemplate(unittest.TestCase):

    def test_all_fields_optional(self) -> None:
        m = MetadataTemplate()
        self.assertIsNone(m.name)
        self.assertIsNone(m.unique_pointer)
        self.assertIsNone(m.author)

    def test_fields_accepted(self) -> None:
        m = MetadataTemplate(name="doc.pdf", unique_pointer=GITLAB_POINTER, author="Alice")
        self.assertEqual(m.name, "doc.pdf")
        self.assertEqual(m.unique_pointer, GITLAB_POINTER)
        self.assertEqual(m.author, "Alice")

    def test_extra_fields_are_ignored(self) -> None:
        m = MetadataTemplate(name="doc.pdf", extra_key="ignored")
        self.assertFalse(hasattr(m, "extra_key"))

    def test_strict_str_rejects_int_name(self) -> None:
        with self.assertRaises(ValidationError):
            MetadataTemplate(name=123)


# ---------------------------------------------------------------------------
# InputItem
# ---------------------------------------------------------------------------


class TestInputItem(unittest.TestCase):

    def test_valid(self) -> None:
        item = InputItem(content="hello", metadata=MetadataTemplate())
        self.assertEqual(item.content, "hello")

    def test_empty_content_raises(self) -> None:
        with self.assertRaises(ValidationError):
            InputItem(content="", metadata=MetadataTemplate())

    def test_missing_content_raises(self) -> None:
        with self.assertRaises(ValidationError):
            InputItem(metadata=MetadataTemplate())

    def test_missing_metadata_raises(self) -> None:
        with self.assertRaises(ValidationError):
            InputItem(content="hello")

    def test_extra_fields_are_ignored(self) -> None:
        item = InputItem(content="hello", metadata=MetadataTemplate(), extra="x")
        self.assertFalse(hasattr(item, "extra"))

    def test_strict_str_rejects_int_content(self) -> None:
        with self.assertRaises(ValidationError):
            InputItem(content=123, metadata=MetadataTemplate())


# ---------------------------------------------------------------------------
# ClassificationResult
# ---------------------------------------------------------------------------


class TestClassificationResult(unittest.TestCase):

    def test_valid_via_alias(self) -> None:
        r = ClassificationResult(**{"Security-class": "Public", "unique_pointer": GITLAB_POINTER})
        self.assertEqual(r.security_class, "Public")
        self.assertEqual(r.unique_pointer, GITLAB_POINTER)

    def test_valid_via_field_name(self) -> None:
        """populate_by_name=True allows using security_class directly."""
        r = ClassificationResult(security_class="Internal", unique_pointer=GITLAB_POINTER)
        self.assertEqual(r.security_class, "Internal")

    def test_serializes_with_alias(self) -> None:
        r = ClassificationResult(security_class="Sensitive", unique_pointer=GITLAB_POINTER)
        data = r.model_dump(by_alias=True)
        self.assertIn("Security-class", data)
        self.assertNotIn("security_class", data)

    def test_serializes_with_field_name(self) -> None:
        r = ClassificationResult(security_class="Confidential", unique_pointer=GITLAB_POINTER)
        data = r.model_dump(by_alias=False)
        self.assertIn("security_class", data)

    def test_all_valid_labels_accepted(self) -> None:
        for label in ("Public", "Internal", "Sensitive", "Confidential"):
            r = ClassificationResult(security_class=label)
            self.assertEqual(r.security_class, label)

    def test_invalid_label_raises(self) -> None:
        with self.assertRaises(ValidationError):
            ClassificationResult(security_class="TopSecret")

    def test_unique_pointer_defaults_to_none(self) -> None:
        r = ClassificationResult(security_class="Public")
        self.assertIsNone(r.unique_pointer)

    def test_missing_security_class_raises(self) -> None:
        with self.assertRaises(ValidationError):
            ClassificationResult(unique_pointer=GITLAB_POINTER)


# ---------------------------------------------------------------------------
# PointerRequest
# ---------------------------------------------------------------------------


class TestPointerRequest(unittest.TestCase):

    def test_valid_single_pointer(self) -> None:
        r = PointerRequest(pointers=[GITLAB_POINTER])
        self.assertEqual(r.pointers, [GITLAB_POINTER])

    def test_valid_multiple_pointers(self) -> None:
        pointers = [GITLAB_POINTER, "https://gitlab.dms-lookup.com/api/v4/projects/6/repository/files/other.md"]
        r = PointerRequest(pointers=pointers)
        self.assertEqual(len(r.pointers), 2)

    def test_empty_list_raises(self) -> None:
        with self.assertRaises(ValidationError):
            PointerRequest(pointers=[])

    def test_missing_pointers_raises(self) -> None:
        with self.assertRaises(ValidationError):
            PointerRequest()

    def test_strict_str_rejects_int_pointer(self) -> None:
        with self.assertRaises(ValidationError):
            PointerRequest(pointers=[123])


# ---------------------------------------------------------------------------
# SummaryResult
# ---------------------------------------------------------------------------


class TestSummaryResult(unittest.TestCase):

    def test_valid(self) -> None:
        s = SummaryResult(summary="A great summary.")
        self.assertEqual(s.summary, "A great summary.")

    def test_missing_summary_raises(self) -> None:
        with self.assertRaises(ValidationError):
            SummaryResult()

    def test_strict_str_rejects_int(self) -> None:
        with self.assertRaises(ValidationError):
            SummaryResult(summary=123)


if __name__ == "__main__":
    unittest.main()
