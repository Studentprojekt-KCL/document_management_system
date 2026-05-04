"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

TIMEOUT: int = 120

CLASSIFICATION: str = "security_class"
IS_DOCUMENT: str = "is_document"
MODIFIED: str = "modified"
UNIQUE_POINTER: str = "unique_pointer"
CONTENT: str = "content"

BOOLEAN_CATEGORIES: set[str] = {IS_DOCUMENT, MODIFIED}
RAW_CATEGORIES: set[str] = {UNIQUE_POINTER, CLASSIFICATION}

CONVERTABLE_TYPES: list[str] = ["255044462d", "504b0304"]  # PDF signature  # ZIP DOCX PPTX ODT XLSX ...
