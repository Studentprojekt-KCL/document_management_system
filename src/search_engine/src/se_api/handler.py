"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from copy import deepcopy

from asyncio import Lock, get_event_loop

from se_api.constants import CLASSIFICATION, UNIQUE_POINTER
from se_api.services.index_pipeline import IndexPipeline
from se_api.services.classifier import Classifier
from se_api.services.connector import Connector
from se_api.services.search_engine import SearchEngine

from shared_functions.dmis_logger import dms_info, dms_warning


class Handler:
    """Handler for internal processing.

    Attributes:
        connector: Connector service.
        search_engine: Search engine service.
    """

    connector: Connector
    classifier: Classifier
    search_engine: SearchEngine
    index_pipeline: IndexPipeline | None

    indexing: Lock

    def __init__(self) -> None:
        """Constructor"""
        self.connector = Connector()
        self.search_engine = SearchEngine()
        self.classifier = Classifier()
        self.index_pipeline = None
        self.indexing = Lock()

    async def init(self) -> None:
        """Init handler"""

        fields: list[str] | None = await self.connector.get_fields()
        self.search_engine.init(fields)

    async def close(self) -> None:
        """Clean up"""
        if self.index_pipeline is not None:
            self.index_pipeline.stop()
        await self.connector.close()
        await self.classifier.close()
        await self.search_engine.close()

    async def reset(self) -> None:
        """Reset the connector."""
        await self.close()
        del self.search_engine
        del self.connector
        del self.classifier
        self.search_engine = SearchEngine()
        self.connector = Connector()
        self.classifier = Classifier()
        fields: list[str] | None = await self.connector.get_fields()
        self.search_engine.reset(fields)
        self.connector.write_subdata({})
        if self.indexing.locked():
            self.indexing.release()
        dms_info("Search engine was reset.")

    def get_classifications(self) -> list[str]:
        """Get list of classifications.

        Returns: list of classifications.
        """
        classifications = deepcopy(self.classifier.LABELS)
        classifications.append("Pending")
        return classifications

    async def find_matching(self, pointer: str, authorization: str | None, count: int = 10) -> list[dict]:
        """Grab pointers for matching files.

        Args:
            pointer: file to compare with.
            count: number of results.
        Returns: the matching pointers and their scores.
        """
        matches = await self.search_engine.find_matching(pointer, count)
        files: list | None = await self.connector.fetch_files(list(matches.keys()), authorization)
        if files is None:
            return []
        for file in files:
            unique_pointer = file.get(UNIQUE_POINTER, "")
            file.update({"score": matches.get(unique_pointer, 0)})
        return files

    def grab_searchable_fields(self) -> set:
        """Grab searchable fields.

        Returns a set with the fields.
        """
        fields = self.search_engine.categories
        fields.remove("is_document")
        fields.add("documents_only")
        return fields

    async def set_classification(self, change: dict[str, str], authorization: str | None) -> dict[str, str]:
        """Set the classification of a file.

        Args:
            change: dict containing the unique pointer and new classification.
        Returns: dict containing the unique pointer, classification, and if edited.
        """

        pointer: str | None = change.get(UNIQUE_POINTER)
        classification: str | None = change.get(CLASSIFICATION)
        if pointer is None or classification is None:
            return {}
        if classification not in self.classifier.LABELS:
            return {}
        files = await self.connector.fetch_files([pointer], authorization)
        if not files:
            return {}
        if await self.search_engine.set_classification(pointer, classification) is None:
            return {}
        if files:
            file: dict = files[0]
            file.update({CLASSIFICATION: classification})
            return file
        return {}

    async def clean_misses(self, matches: list[str], grabbed: list[dict]) -> None:
        """Remove missing files from cache and index.

        Args:
            matches: list of pointers
            grabbed: list of file dicts.
        """

        grabs = [grab.get("unique_pointer") for grab in grabbed]
        for match in matches:
            if match in grabs:
                continue
            await self.search_engine.remove_file(match)

    async def preform_search(self, content: dict, count: int, offset: int, authorization: str | None) -> list:
        """Get get files from collectors preform the search, returns a list.

        Args:
            content: query per field.
            count: how many results.
            offset: how deep in to grab the results.
        Returns: matching files or None.
        """

        if count <= 0:
            dms_warning(f"Count result count is invalid. (count: {count}).")
            return []
        if offset < 0:
            dms_warning(f"Offset is invalid. (offset: {offset}).")
            return []

        if not self.indexing.locked():
            loop = get_event_loop()
            loop.create_task(self._handle_new(authorization))

        matches, metadata = self.search_engine.query_files(content, count, offset)
        files: list[dict] | None = await self.connector.fetch_files(matches, authorization)
        if files is None:
            return []
        await self.clean_misses(matches, files)
        for file in files:
            file.update(metadata.get(file.get(UNIQUE_POINTER, ""), {}))
        return files

    async def _handle_new(self, authorization: str | None) -> None:
        """Grab connector stream output and pipe it into search engine."""
        await self.indexing.acquire()
        self.index_pipeline = IndexPipeline(self.search_engine, self.connector, self.classifier)
        await self.index_pipeline.run(authorization)
        self.indexing.release()
