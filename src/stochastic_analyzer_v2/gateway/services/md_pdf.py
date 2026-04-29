"""Simple endpoint functionality for coverting a md formatted string to a PDF"""

from io import BytesIO

from markdown_pdf import MarkdownPdf, Section

from shared_functions.dmis_logger import dms_warning


class PdfConverter:
    """Convert markdown text to pdf bytes"""

    def convert(self, md: str) -> bytes | None:
        """same as above lol"""
        try:
            pdf = MarkdownPdf()
            pdf.add_section(Section(md))
            out = BytesIO()
            pdf.save_bytes(out)
            return out.getvalue()
        except Exception as err:
            dms_warning(f"PDF conversion failed: {err}")
            return None
