"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

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

    def preform_search(self, request: str, k: int) -> list[str] | None:
        """Get get files from collectors preform the search, returns a list.

        Args:
            request: Query to perform.

        Returns:
            Returns matching files or None.
        """

        new_files: list = self.connector.get_file_pointers()

        if new_files:
            files = self.connector.get_files()
            if files:
                if self.search_engine.have_new_category(files[0]):
                    self.search_engine.rebuild()
                    self.connector.reset()
                    files = self.connector.get_files()
                self.search_engine.add_files(files)

        matches: list = self.search_engine.query_files(request, k)
        return matches
