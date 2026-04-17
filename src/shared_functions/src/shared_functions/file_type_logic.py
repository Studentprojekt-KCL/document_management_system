"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import json
from importlib import resources
from shared_functions.dmis_logger import dms_error


def get_file_resource() -> list:
    """Read data/file_types.json."""
    text = resources.read_text("shared_functions.data", "file_types.json")
    list_object = json.loads(text)
    if not isinstance(list_object, list):
        dms_error("documents_only_types.json had an unexpected format, has something changed?")
        return []
    return list_object


def get_documents_only_rescource() -> list:
    """Read data/documents_only_types.json."""
    text = resources.read_text("shared_functions.data", "documents_only_types.json")
    list_object = json.loads(text)
    if not isinstance(list_object, list):
        dms_error("documents_only_types.json had an unexpected format, has something changed?")
        return []
    return list_object


def determine_file_type(file_name: str | None, file_extensions: list, descriptions: dict) -> dict[str, str]:
    """Determine file type and short decribing phrase for a given file type.

    Args:
    ----
        file_name: Full name of file.
        file_extensions: A list of defined extensions.
        descriptions: Dict structured {<EXTENSION>: <DESCRIPTION>}

    Returns:
    -------
        {"file_type": <EXTENSION>, "file_type_description": <DESCRIPTION>}
    """
    for extension in file_extensions:
        if not isinstance(file_name, str):
            break
        if file_name.endswith(extension):
            return {"file_type": extension, "file_type_description": descriptions.get(extension)}

    return {"file_type": "Unknown", "file_type_description": "Unknown"}
