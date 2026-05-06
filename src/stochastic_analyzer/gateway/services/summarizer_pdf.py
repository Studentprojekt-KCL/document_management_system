"""Markdown to PDF conversion."""

from io import BytesIO

from markdown_pdf import MarkdownPdf, Section


class PdfConverter:
    """Converts markdown text to PDF bytes.

    Attributes:
        toc_level: Table of contents depth.
    """

    def __init__(self, toc_level: int = 2) -> None:
        self.toc_level = toc_level

    def convert(self, md: str) -> bytes:
        """Convert markdown string to PDF bytes.

        Args:
            md: Markdown string.

        Returns:
            PDF file as bytes.
        """
        pdf = MarkdownPdf(toc_level=self.toc_level, optimize=True)
        pdf.add_section(Section(md))
        out = BytesIO()
        pdf.save_bytes(out)
        result = out.getvalue()
        out.close()
        return result
