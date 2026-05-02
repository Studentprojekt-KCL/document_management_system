"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

TIMEOUT: int = 120

CLASSIFICATION: str = "classification"
IS_DOCUMENT: str = "is_document"
MODIFIED: str = "modified"
UNIQUE_POINTER: str = "unique_pointer"

BOOLEAN_CATEGORIES: set[str] = {IS_DOCUMENT, MODIFIED}
RAW_CATEGORIES: set[str] = {UNIQUE_POINTER, CLASSIFICATION}
