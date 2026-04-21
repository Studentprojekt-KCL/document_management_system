"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Unit tests for the stochastic_analyzer PDF conversion helper.
"""

import unittest
from unittest.mock import MagicMock, patch

from gateway.services.summarizer_pdf import PdfConverter


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
        self.assertGreater(len(result), 0)

    def test_pdf_magic_bytes(self) -> None:
        """Returned bytes start with the PDF magic number %PDF."""
        result = self.converter.convert("# Title\nContent here.")
        self.assertEqual(result[:4], b"%PDF", "Output does not appear to be a valid PDF")

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_string(self) -> None:
        """convert() handles an empty string without raising."""
        result = self.converter.convert("")
        self.assertIsInstance(result, bytes)

    def test_plain_text_no_markdown(self) -> None:
        """convert() handles plain text with no markdown syntax."""
        result = self.converter.convert("Just a plain sentence with no markdown.")
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
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_unicode_content(self) -> None:
        """convert() handles unicode characters without raising."""
        md = "# Ünïcödé\nSwedish: åäö. Chinese: 你好. Arabic: مرحبا."
        result = self.converter.convert(md)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_large_document(self) -> None:
        """convert() handles a large markdown document without errors."""
        md = "# Large Doc\n" + ("Paragraph text. " * 500 + "\n\n") * 20
        result = self.converter.convert(md)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    # ------------------------------------------------------------------
    # Determinism
    # ------------------------------------------------------------------

    def test_different_inputs_produce_different_outputs(self) -> None:
        """Different markdown content produces different PDF bytes."""
        result_a = self.converter.convert("# Document A\nContent A.")
        result_b = self.converter.convert("# Document B\nContent B.")
        self.assertNotEqual(result_a, result_b)

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def test_default_toc_level_is_two(self) -> None:
        """PdfConverter defaults to toc_level=2."""
        self.assertEqual(self.converter.toc_level, 2)

    def test_custom_toc_level_is_stored(self) -> None:
        """PdfConverter stores a custom toc_level passed to __init__."""
        converter = PdfConverter(toc_level=4)
        self.assertEqual(converter.toc_level, 4)

    # ------------------------------------------------------------------
    # Internal wiring (mocked)
    # ------------------------------------------------------------------

    @patch("gateway.services.summarizer_pdf.MarkdownPdf")
    def test_bytesio_is_closed_after_convert(self, mock_pdf_cls: MagicMock) -> None:
        """The internal BytesIO buffer is always closed after convert() returns."""
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value = mock_pdf
        mock_pdf.save_bytes.side_effect = lambda buf: buf.write(b"%PDF-fake")

        self.converter.convert("# Test\nContent.")

        # Retrieve the BytesIO instance that was passed to save_bytes and then closed
        captured_buf = mock_pdf.save_bytes.call_args[0][0]
        self.assertTrue(captured_buf.closed)

    @patch("gateway.services.summarizer_pdf.MarkdownPdf")
    def test_markdown_pdf_instantiated_with_correct_args(self, mock_pdf_cls: MagicMock) -> None:
        """MarkdownPdf is instantiated with the converter's toc_level and optimize=True."""
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value = mock_pdf
        mock_pdf.save_bytes.side_effect = lambda buf: buf.write(b"%PDF-fake")

        self.converter.convert("# Hello\nWorld.")

        mock_pdf_cls.assert_called_once_with(toc_level=self.converter.toc_level, optimize=True)

    @patch("gateway.services.summarizer_pdf.MarkdownPdf")
    def test_custom_toc_level_passed_to_markdown_pdf(self, mock_pdf_cls: MagicMock) -> None:
        """MarkdownPdf receives the custom toc_level when it differs from the default."""
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value = mock_pdf
        mock_pdf.save_bytes.side_effect = lambda buf: buf.write(b"%PDF-fake")

        PdfConverter(toc_level=3).convert("# Hello\nWorld.")

        mock_pdf_cls.assert_called_once_with(toc_level=3, optimize=True)

    @patch("gateway.services.summarizer_pdf.Section")
    @patch("gateway.services.summarizer_pdf.MarkdownPdf")
    def test_section_receives_exact_markdown_string(self, mock_pdf_cls: MagicMock, mock_section_cls: MagicMock) -> None:
        """Section is instantiated with the exact markdown string passed to convert()."""
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value = mock_pdf
        mock_pdf.save_bytes.side_effect = lambda buf: buf.write(b"%PDF-fake")

        md = "# My Section\nBody text."
        self.converter.convert(md)

        mock_section_cls.assert_called_once_with(md)


if __name__ == "__main__":
    unittest.main()
