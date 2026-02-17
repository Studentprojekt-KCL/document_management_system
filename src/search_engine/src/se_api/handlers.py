"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from se_api.models import File, Query, Metadata


def preform_search(request: Query) -> list[File] | None:
    """Get get files from collectors preform the search, returns a list.

    Keyword arguments:
    query -- the query to preform.
    """

    preform_query(request.query)
    metadata_search(request.metadata)

    # request files
    # quick search

    return []


def preform_query(query: str | None) -> None:
    """Preform query"""
    if query is None:
        return

    return


def metadata_search(metadata: Metadata | None) -> None:
    """Preform meta search"""
    if metadata is None:
        return

    return
