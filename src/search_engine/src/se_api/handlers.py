"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from se_api.models import File, Query, Metadata
from se_api.services.connector import Connector
from se_api.services.search_engine import SearchEngine

class Handler:
    connector: Connector
    search_engine: SearchEngine

    def __init__(self) -> None:
        self.connector = Connector()
        self.search_engine = SearchEngine()

    def preform_search(self, request: Query) -> list[File] | None:
        """Get get files from collectors preform the search, returns a list.

        Keyword arguments:
        query -- the query to preform.
        """

        if request.query is None:
            return

        files: list[File] = self.connector.get_files()
        self.search_engine.add_files(files)
        pointers: list[str] = self.search_engine.query_files(request.query, k=10)

        files = []

        for pointer in pointers:
            file: File | None = self.connector.get_file(pointer)
            if file is not None:
                files.append(file)

        return files
                
