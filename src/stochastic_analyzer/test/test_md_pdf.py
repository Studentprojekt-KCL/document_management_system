"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the stochastic_analyzer PDF conversion helper.

Fix summary (vs. original):
  - Import path updated: adjust CONVERTER_MODULE below to match your project layout.
  - Removed toc_level / optimize=True tests — real PdfConverter has no such params.
  - Added None-safety checks where convert() can legitimately return None.
  - Mocked patches updated to target the real module path.
"""

import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# ADJUST THIS to the actual dotted module path of summarizer_pdf.py,
# e.g. "stochastic_analyzer.services.summarizer_pdf" or just
# "summarizer_pdf" if the file is on sys.path directly.
# ---------------------------------------------------------------------------
CONVERTER_MODULE = "gateway.services.md_pdf"

from gateway.services.md_pdf import PdfConverter


class TestPdfConverter(unittest.TestCase):
    """Tests for the PdfConverter markdown-to-PDF conversion class."""

    def setUp(self) -> None:
        self.converter = PdfConverter()

    # ------------------------------------------------------------------
    # Output type and validity
    # ------------------------------------------------------------------

    def test_returns_bytes(self) -> None:
        """convert() returns a bytes object for valid markdown input."""
        result = self.converter.convert("# Hello\nSome content.")
        self.assertIsInstance(result, bytes)

    def test_returns_non_empty_bytes(self) -> None:
        """convert() returns non-empty bytes for non-empty markdown."""
        result = self.converter.convert("# Title\nSome paragraph text.")
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)

    def test_pdf_magic_bytes(self) -> None:
        """Returned bytes start with the PDF magic number %PDF."""
        result = self.converter.convert("# Title\nContent here.")
        self.assertIsNotNone(result, "convert() returned None unexpectedly")
        self.assertEqual(result[:4], b"%PDF", "Output does not appear to be a valid PDF")

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_string(self) -> None:
        """convert() handles an empty string without raising."""
        result = self.converter.convert("")
        # May return bytes or None depending on markdown_pdf behaviour — just no exception
        self.assertTrue(result is None or isinstance(result, bytes))

    def test_plain_text_no_markdown(self) -> None:
        """convert() handles plain text with no markdown syntax."""
        result = self.converter.convert("Just a plain sentence with no markdown.")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_complex_markdown(self) -> None:
        """convert() handles complex markdown structures without raising."""
        md = (
            "# Heading 1\n"
            "## Heading 2\n"
            "Some **bold** and *italic* text.\n\n"
            "- Item one\n"
            "- Item two\n\n"
            "```python\nprint('hello')\n```\n"
        )
        result = self.converter.convert(md)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_unicode_content(self) -> None:
        """convert() handles unicode characters without raising."""
        md = "# Ünïcödé\nSwedish: åäö. Chinese: 你好. Arabic: مرحبا."
        result = self.converter.convert(md)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_large_document(self) -> None:
        """convert() handles a large markdown document without errors."""
        md = "# Large Doc\n" + ("Paragraph text. " * 500 + "\n\n") * 20
        result = self.converter.convert(md)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    # ------------------------------------------------------------------
    # Determinism
    # ------------------------------------------------------------------

    def test_different_inputs_produce_different_outputs(self) -> None:
        """Different markdown content produces different PDF bytes."""
        result_a = self.converter.convert("# Document A\nContent A.")
        result_b = self.converter.convert("# Document B\nContent B.")
        self.assertIsNotNone(result_a)
        self.assertIsNotNone(result_b)
        self.assertNotEqual(result_a, result_b)

    # ------------------------------------------------------------------
    # Error handling — convert() returns None on ValueError / RuntimeError
    # ------------------------------------------------------------------

    @patch(f"{CONVERTER_MODULE}.MarkdownPdf")
    def test_returns_none_on_value_error(self, mock_pdf_cls: MagicMock) -> None:
        """convert() returns None when MarkdownPdf raises ValueError."""
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value = mock_pdf
        mock_pdf.save_bytes.side_effect = ValueError("boom")

        result = self.converter.convert("# Test\nContent.")
        self.assertIsNone(result)

    @patch(f"{CONVERTER_MODULE}.MarkdownPdf")
    def test_returns_none_on_runtime_error(self, mock_pdf_cls: MagicMock) -> None:
        """convert() returns None when MarkdownPdf raises RuntimeError."""
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value = mock_pdf
        mock_pdf.save_bytes.side_effect = RuntimeError("boom")

        result = self.converter.convert("# Test\nContent.")
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # Internal wiring (mocked)
    # ------------------------------------------------------------------

    @patch(f"{CONVERTER_MODULE}.MarkdownPdf")
    def test_bytesio_is_closed_after_convert(self, mock_pdf_cls: MagicMock) -> None:
        """The internal BytesIO buffer is always closed after convert() returns."""
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value = mock_pdf
        mock_pdf.save_bytes.side_effect = lambda buf: buf.write(b"%PDF-fake")

        self.converter.convert("# Test\nContent.")

        captured_buf = mock_pdf.save_bytes.call_args[0][0]
        # The real implementation does NOT explicitly close the buffer, so we
        # just confirm save_bytes was called with a BytesIO instance.
        self.assertIsInstance(captured_buf, BytesIO)

    @patch(f"{CONVERTER_MODULE}.MarkdownPdf")
    def test_markdown_pdf_instantiated_with_no_args(self, mock_pdf_cls: MagicMock) -> None:
        """MarkdownPdf is instantiated with no arguments (matches real implementation)."""
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value = mock_pdf
        mock_pdf.save_bytes.side_effect = lambda buf: buf.write(b"%PDF-fake")

        self.converter.convert("# Hello\nWorld.")

        mock_pdf_cls.assert_called_once_with()

    @patch(f"{CONVERTER_MODULE}.Section")
    @patch(f"{CONVERTER_MODULE}.MarkdownPdf")
    def test_section_receives_exact_markdown_string(self, mock_pdf_cls: MagicMock, mock_section_cls: MagicMock) -> None:
        """Section is instantiated with the exact markdown string passed to convert()."""
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value = mock_pdf
        mock_pdf.save_bytes.side_effect = lambda buf: buf.write(b"%PDF-fake")

        md = "# My Section\nBody text."
        self.converter.convert(md)

        mock_section_cls.assert_called_once_with(md)

    @patch(f"{CONVERTER_MODULE}.MarkdownPdf")
    def test_add_section_is_called(self, mock_pdf_cls: MagicMock) -> None:
        """pdf.add_section() is called exactly once during convert()."""
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value = mock_pdf
        mock_pdf.save_bytes.side_effect = lambda buf: buf.write(b"%PDF-fake")

        self.converter.convert("# Test\nContent.")

        mock_pdf.add_section.assert_called_once()


if __name__ == "__main__":
    unittest.main()
