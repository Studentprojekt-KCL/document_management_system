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
            with BytesIO() as out:
                pdf.save_bytes(out)
                data = out.getvalue()
        except (ValueError, RuntimeError, OSError, KeyError, AttributeError, TypeError) as err:
            dms_warning(f"PDF conversion failed: {type(err).__name__}: {err}")
            return None

        if not data.startswith(b"%PDF"):
            dms_warning("PDF conversion produced non-PDF output")
            return None
        return data
