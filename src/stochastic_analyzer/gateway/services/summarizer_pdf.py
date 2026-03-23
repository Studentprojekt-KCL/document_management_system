"""Batch document summarization via external Ministral LLM."""

from io import BytesIO
from markdown_pdf import MarkdownPdf, Section


def md_to_pdf(md: str) -> bytes:
    """Convert markdownn to pdf.

    Args:
        md: markdown string
    Retruns: PDF file as bytes.
    """
    pdf = MarkdownPdf(toc_level=2, optimize=True)
    pdf.add_section(Section(md))
    out = BytesIO()
    pdf.save_bytes(out)
    result = out.getvalue()
    out.close()
    return result
