"""Simple endpoint functionality for coverting a md formatted string to a PDF"""

from io import BytesIO

from markdown_pdf import MarkdownPdf, Section

from shared_functions.dmis_logger import dms_warning


class PdfConverter:
    """Convert markdown text to pdf bytes"""

    def convert(self, md: str) -> bytes | None:
        """Convert a markdown string to PDF bytes."""
        if not isinstance(md, str):
            dms_warning(f"PDF conversion expected str, got {type(md).__name__}")
            return None
        if not md.strip():
            dms_warning("PDF conversion received empty markdown")
            return None
        try:
            pdf = MarkdownPdf()
            pdf.add_section(Section(md))
            out = BytesIO()
            pdf.save_bytes(out)
            return out.getvalue()
        except (ValueError, RuntimeError) as err:
            dms_warning(f"PDF conversion failed: {err}")
            return None
