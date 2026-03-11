"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from dmis_logger import dms_info, dms_warning
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

    def reset_connector(self) -> None:
        """Reset the connector."""
        self.search_engine = SearchEngine()
        self.connector = Connector()
        dms_info("Search engine was reset.")

    def preform_search(self, request: str, k: int, p: int) -> list[str]:
        """Get get files from collectors preform the search, returns a list.

        Args:
            request: Query to perform.

        Returns:
            Returns matching files or None.
        """

        if k <= 0 or p < 1:
            dms_warning(f"Either page size or page index is invalid. (p: {p}, k: {k}).")
            return []

        files: list = self.connector.get_files()
        if files:
            dms_info(f"New files in connector reindexing, number of files: {len(files)}.")
            if files:
                if self.search_engine.have_new_category(files[0]):
                    self.search_engine.rebuild()
                    self.connector.reset()
                    files = self.connector.get_files()
                self.search_engine.add_files(files)

        matches: list = self.search_engine.query_files(request, k * p)

        matching_files: list = []

        for i in range(k * (p - 1), len(matches)):
            file: dict | None = self.connector.get_file(matches[i])

            if file is None:
                continue

            metadata: dict | None = file.get("metadata")
            if metadata is None:
                continue

            matching_files.append(metadata)

        return matching_files
