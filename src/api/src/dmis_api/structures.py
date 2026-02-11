"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from typing import Any

from pydantic import BaseModel


class Search(BaseModel):
    """Basic search structure."""

    params: dict


class IndexRequest(BaseModel):
    """Defined structure for DMIS API index endpoint."""

    data: dict[Any, Any]  # type: ignore
    search: Search

    model_config: dict = {  # type: ignore
        "json_schema_extra": {
            "examples": [
                {
                    "data": {"key": "value"},
                    "search": {
                        "params": {
                            "created_after": "946702800",
                            "created_before": "1293858000",
                            "owner": "John Doe",
                            "search_term": "Example",
                        }
                    },
                }
            ]
        }
    }
