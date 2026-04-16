import json
from importlib import resources

def get_file_resource():
    """Read data/file_types.json."""
    text = resources.read_text("shared_functions.data", "file_types.json")
    return json.loads(text)

def get_documents_only_rescource():
    """Read data/documents_only_types.json."""
    text = resources.read_text("shared_functions.data", "documents_only_types.json")
    return json.loads(text)

def determine_file_type(file_name: str, file_extensions: list, descriptions: dict):
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
        if file_name.endswith(extension):
            return {"file_type": extension, "file_type_description": descriptions.get(file_name)}
