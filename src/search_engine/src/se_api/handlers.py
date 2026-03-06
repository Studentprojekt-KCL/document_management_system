"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from se_api.models.file import File
from se_api.models.query import Query
from se_api.services.connector import Connector
from se_api.services.search_engine import SearchEngine


class Handler:
    """Handler for internal processing.

    Attributes:
        connector: Connector service.
        search_engine: Search engine service.
    """

    connector: Connector
    search_engine: SearchEngine

    def __init__(self) -> None:
        self.connector = Connector()
        self.search_engine = SearchEngine()

    def preform_search(self, request: Query) -> list[File] | None:
        """Get get files from collectors preform the search, returns a list.

        Args:
            request: Query to perform.

        Returns:
            Returns matching files or None.
        """

        new_files: list[str] = self.connector.get_file_pointers()
        if len(new_files) != 0:
            files: list[File] = self.connector.get_files()
            self.search_engine.add_files(files)
        matches: list[str] = self.search_engine.query_files(request, k=10)
        updated_files: list[File] = []
        for match in matches:
            file: File | None = self.connector.get_file(match)
            if file is not None:
                updated_files.append(file)
        return updated_files
