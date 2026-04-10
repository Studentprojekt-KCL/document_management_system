"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from dmis_logger import dms_info, dms_warning
from se_api.services.connector import Connector
from se_api.services.query import Query
from se_api.services.search_engine import SearchEngine


class Handler:
    """Handler for internal processing.

    Attributes:
        connector: Connector service.
        search_engine: Search engine service.
    """

    connector: Connector
    query: Query
    search_engine: SearchEngine

    def __init__(self) -> None:
        self.connector = Connector()
        self.search_engine = SearchEngine()
        self.query = Query()

    def reset(self) -> None:
        """Reset the connector."""
        self.search_engine = SearchEngine()
        self.connector = Connector()
        self.query = Query()
        dms_info("Search engine was reset.")

    def clean_misses(self, matches: list[str], grabbed: list[dict]) -> None:
        grabs = [grab.get("unique_pointer") for grab in grabbed]
        for match in matches:
            if match in grabs:
                continue
            self.search_engine.remove_file(match)
            self.query.cache.remove_classification(match)

    def preform_search(self, request: str, count: int, offset: int) -> list:
        """Get get files from collectors preform the search, returns a list.

        Args:
            request: Query to perform.

        Returns:
            Returns matching files or None.
        """

        if count <= 0:
            dms_warning(f"Count result count is invalid. (count: {count}).")
            return []
        if offset < 0:
            dms_warning(f"Offset is invalid. (offset: {offset}).")
            return []

        if self.connector.reindex_needed():  # This endpoint is approx 3x faster
            new_files: list[dict] = self.connector.get_files()
            if new_files:
                if self.search_engine.have_new_category(new_files[0]):
                    self.search_engine.rebuild()
                    self.connector.reset()
                    new_files = self.connector.get_files()
                self.search_engine.add_files(new_files)
        matches: list = self.search_engine.query_files(request, offset + count)[offset : count + offset]
        files: list[dict] = self.connector.fetch_files(matches)
        self.clean_misses(matches, files)
        classifications: dict = self.query.classify(files)        
        for file in files:
            unique_pointer: str = file.get("unique_pointer", "")
            classification: str = classifications.get(unique_pointer, "")
            file.update({"security_class": classification})

        return files
