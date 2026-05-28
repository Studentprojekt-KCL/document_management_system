"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the gateway Pydantic schemas.
"""

import unittest

from pydantic import ValidationError

from gateway.schemas import (
    InputItem,
    MarkdownRequest,
    MetadataTemplate,
    PointerRequest,
)

GITLAB_POINTER = "https://gitlab.dms-lookup.com/api/v4/projects/7/repository/files/doc.txt"

# ---------------------------------------------------------------------------
# MetadataTemplate
# ---------------------------------------------------------------------------


class TestMetadataTemplate(unittest.TestCase):

    def test_valid_required_fields_only(self) -> None:
        m = MetadataTemplate(unique_pointer=GITLAB_POINTER)
        self.assertEqual(m.unique_pointer, GITLAB_POINTER)

    def test_name_defaults_to_none(self) -> None:
        m = MetadataTemplate(unique_pointer=GITLAB_POINTER)
        self.assertIsNone(m.name)

    def test_name_accepted(self) -> None:
        m = MetadataTemplate(unique_pointer=GITLAB_POINTER, name="doc.pdf")
        self.assertEqual(m.name, "doc.pdf")

    def test_missing_unique_pointer_raises(self) -> None:
        with self.assertRaises(ValidationError):
            MetadataTemplate()

    def test_strict_str_rejects_int_pointer(self) -> None:
        with self.assertRaises(ValidationError):
            MetadataTemplate(unique_pointer=123)

    def test_strict_str_rejects_int_name(self) -> None:
        with self.assertRaises(ValidationError):
            MetadataTemplate(unique_pointer=GITLAB_POINTER, name=123)


# ---------------------------------------------------------------------------
# InputItem
# ---------------------------------------------------------------------------


class TestInputItem(unittest.TestCase):

    def test_valid(self) -> None:
        item = InputItem(content="hello", metadata=MetadataTemplate(unique_pointer=GITLAB_POINTER))
        self.assertEqual(item.content, "hello")

    def test_missing_content_raises(self) -> None:
        with self.assertRaises(ValidationError):
            InputItem(metadata=MetadataTemplate(unique_pointer=GITLAB_POINTER))

    def test_missing_metadata_raises(self) -> None:
        with self.assertRaises(ValidationError):
            InputItem(content="hello")

    def test_strict_str_rejects_int_content(self) -> None:
        with self.assertRaises(ValidationError):
            InputItem(content=123, metadata=MetadataTemplate(unique_pointer=GITLAB_POINTER))

    def test_metadata_must_have_unique_pointer(self) -> None:
        with self.assertRaises(ValidationError):
            InputItem(content="hello", metadata=MetadataTemplate())


# ---------------------------------------------------------------------------
# MarkdownRequest
# ---------------------------------------------------------------------------


class TestMarkdownRequest(unittest.TestCase):

    def test_valid(self) -> None:
        r = MarkdownRequest(markdown="# Hello")
        self.assertEqual(r.markdown, "# Hello")

    def test_missing_markdown_raises(self) -> None:
        with self.assertRaises(ValidationError):
            MarkdownRequest()

    def test_strict_str_rejects_int(self) -> None:
        with self.assertRaises(ValidationError):
            MarkdownRequest(markdown=123)


# ---------------------------------------------------------------------------
# PointerRequest
# ---------------------------------------------------------------------------


class TestPointerRequest(unittest.TestCase):

    def test_valid_single_pointer(self) -> None:
        r = PointerRequest(pointers=[GITLAB_POINTER])
        self.assertEqual(r.pointers, [GITLAB_POINTER])

    def test_valid_multiple_pointers(self) -> None:
        pointers = [
            GITLAB_POINTER,
            "https://gitlab.dms-lookup.com/api/v4/projects/6/repository/files/other.md",
        ]
        r = PointerRequest(pointers=pointers)
        self.assertEqual(len(r.pointers), 2)

    def test_missing_pointers_raises(self) -> None:
        with self.assertRaises(ValidationError):
            PointerRequest()

    def test_strict_str_rejects_int_pointer(self) -> None:
        with self.assertRaises(ValidationError):
            PointerRequest(pointers=[123])
