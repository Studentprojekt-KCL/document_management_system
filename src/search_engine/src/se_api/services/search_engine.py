"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import json
from os import listdir, remove
from asyncio import Lock, to_thread
from tantivy import (
    Document,
    Index,
    IndexWriter,
    Occur,
    Query,
    SchemaBuilder,
    SearchResult,
    Searcher,
)

from se_api.constants import (
    BOOLEAN_CATEGORIES,
    CLASSIFICATION,
    CONTENT,
    COOKED_CATEGORIES,
    IS_DOCUMENT,
    MODIFIED,
    RAW_CATEGORIES,
    UNIQUE_POINTER,
)

from shared_functions.initialisation_tools import read_env_variable
from shared_functions.file_type_logic import get_documents_only_rescource
from shared_functions.dmis_logger import dms_error, dms_info, dms_warning


class SearchEngine:
    """Search engine service

    Attributes:
        index: The built index from the gathered files.
    """

    index: Index
    categories: set[str]
    index_path: str
    documents_only_extension: list
    writer_lock: Lock
    writer: IndexWriter

    def __init__(self) -> None:
        """Constructor"""
        self.index_path = read_env_variable("SEARCHENG_WORKING_DIRECTORY", required=True).rstrip("/") + "/index"  # type: ignore
        extentions = get_documents_only_rescource()
        self.documents_only_extension = []
        for extention in extentions:
            self.documents_only_extension.extend(extention.get("extension", []))
        self.writer_lock = Lock()

    def _load_fields(self, fetched_fields: list | None) -> list:
        """Prepear fields for usage.

        Args:
            fetched_fields: fields from connector.
        Returns: sorted list of fields
        """
        fields: set = BOOLEAN_CATEGORIES
        fields = fields.union(RAW_CATEGORIES)
        fields = fields.union(COOKED_CATEGORIES)
        if fetched_fields is not None:
            for field in fetched_fields:
                fields.add(field)
        self.categories = fields
        return sorted(list(fields))

    def load_index(self, fetched_fields: list | None) -> bool:
        """Load index and build schema.

        Args:
            fetched_fields: Fetched fields from connectors.
        Returns: true if rebuild, else false.
        """
        rebuild = False
        fields = self._load_fields(fetched_fields)
        schema_builder = SchemaBuilder()
        for category in fields:
            if category in RAW_CATEGORIES:
                schema_builder.add_text_field(category, stored=True, tokenizer_name="raw", fast=True)
            elif category in BOOLEAN_CATEGORIES:
                schema_builder.add_boolean_field(category, stored=True, indexed=True)
            else:
                schema_builder.add_text_field(category, stored=True)
            dms_info(f"Added field {category}")
        schema = schema_builder.build()
        try:
            self.index = Index(schema, path=self.index_path)
            dms_info(f"Loaded index from path {self.index_path}")
        except ValueError:
            dms_warning(f"Directory containing different schema was found in {self.index_path}, removing.")
            for file in listdir(self.index_path):
                remove(f"{self.index_path}/{file}")
            try:
                self.index = Index(schema, path=self.index_path)
                rebuild = True
            except ValueError:
                dms_error(f"Failed loading index directory, path: {self.index_path}.")
        self.writer = self.index.writer()
        return rebuild

    async def close(self) -> None:
        """Graceful shutdown."""
        async with self.writer_lock:
            self.writer.wait_merging_threads()

    def reset(self, fields: list[str] | None) -> None:
        """Reset the search engine."""
        for file in listdir(self.index_path):
            remove(f"{self.index_path}/{file}")
        self.load_index(fields)

    async def set_classification(self, unique_pointer: str, classification: str) -> tuple[str, str] | None:
        """Set the classification of a file in the index.

        Args:
            unique_pointer: pointer for the file.
            classification: new classification.
        """
        self.index.reload()
        searcher = self.index.searcher()
        result = searcher.search(Query.term_query(self.index.schema, field_name=UNIQUE_POINTER, field_value=unique_pointer))
        if not result.hits:
            return None
        doc_address = result.hits[0][1]
        doc = searcher.doc(doc_address)
        file: dict = {}
        for category in self.categories:
            try:
                file.update({category: doc[category][0]})
            except IndexError:
                dms_warning(f"File '{unique_pointer}' is missing category: '{category}'.")
        file[CLASSIFICATION] = classification
        file[MODIFIED] = True
        async with self.open_writer():
            await self.add_file(file, force=True)
        return (unique_pointer, classification)

    def query_files(self, content: dict[str, str], count: int, offset: int) -> tuple[list[str], dict[str, dict]]:
        """Query through the files in the index.

        Args:
            content: dict with fields and their queries.
            count: number of wanted results.

        Returns:
            List of file pointers with matching content.

        Raises:
            SeAPIException: Potential formatting errors.
        """

        sub_queries: list[tuple] = []
        for field, value in content.items():
            try:
                sub_queries.append(
                    (Occur.Must, self.index.parse_query(value, [field if field != "documents_only" else IS_DOCUMENT]))
                )
            except ValueError:
                dms_warning(f"Failed to create query: '{value}' for field: '{field}'")
            except TypeError:
                dms_warning(f"Value is of wrong type, expected string got '{type(value)}': '{value}'")

        self.index.reload()
        searcher: Searcher = self.index.searcher()
        result: SearchResult = searcher.search(Query.boolean_query(sub_queries), limit=count, offset=offset)
        pointers: list[str] = []
        metadata: dict[str, dict] = {}
        for _, doc_id in result.hits:
            doc: Document = searcher.doc(doc_id)
            try:
                unique_pointer = doc[UNIQUE_POINTER][0]
                metadata.update(
                    {
                        unique_pointer: {
                            CLASSIFICATION: doc[CLASSIFICATION][0],
                            MODIFIED: doc[MODIFIED][0],
                        }
                    }
                )
                pointers.append(unique_pointer)
            except IndexError:
                dms_warning(f"Missing unique_pointer: {doc}")
        return (pointers, metadata)

    async def find_matching(self, unique_pointer: str, count: int) -> tuple[list[str], dict[str, dict]]:
        """Search for matching files.

        Args:
            unique_pointer: file to match with.
        Returns: unique pointers and their score.
        """
        matching: dict = {}
        self.index.reload()
        searcher = self.index.searcher()
        result = searcher.search(Query.term_query(self.index.schema, field_name=UNIQUE_POINTER, field_value=unique_pointer))
        if not result.hits:
            return ([], {})
        doc_address = result.hits[0][1]
        result = searcher.search(Query.more_like_this_query(doc_address), limit=count + 1)
        original_score: int | None = None
        for score, doc_id in result.hits:
            if original_score is None:
                if score == 0:
                    break
                original_score = score
                continue
            doc: Document = searcher.doc(doc_id)
            unique_pointer = doc[UNIQUE_POINTER][0]
            matching.update({unique_pointer: score / original_score})
        return (list(matching.keys()), matching)

    @asynccontextmanager
    async def open_writer(self) -> AsyncGenerator[None]:
        """Init index writer."""
        await self.writer_lock.acquire()
        try:
            yield
            await asyncio.to_thread(self.writer.commit)
        finally:
            self.writer_lock.release()

    def grab_file(self, unique_pointer: str) -> dict:
        """Grab a file from the index.

        Args:
            unique_pointer: the file pointer.
        Returns: file dict.
        """

        self.index.reload()
        searcher: Searcher = self.index.searcher()
        matches = searcher.search(Query.term_query(self.index.schema, UNIQUE_POINTER, unique_pointer))
        if matches.hits:
            doc_id = matches.hits[0][1]
            doc = searcher.doc(doc_id)
            file = {}
            for category in self.categories:
                try:
                    file[category] = doc[category][0]
                except IndexError:
                    file[category] = "N/A"
            return file
        return {}

    async def add_file(self, file: dict, force: bool = False) -> None:
        """Add file to index.

        Requiers init call before and after.

        Args:
            file: file dict
            force: Force change classification field.
        """

        unique_pointer: str | None = file.get(UNIQUE_POINTER)
        if unique_pointer is None:
            dms_warning(f"File is missing unique pointer: {file.update({CONTENT: ""})}.")
            return
        self.index.reload()
        searcher: Searcher = self.index.searcher()
        matches = await to_thread(searcher.search, Query.term_query(self.index.schema, UNIQUE_POINTER, unique_pointer))
        if matches.hits:
            doc_id = matches.hits[0][1]
            doc = await to_thread(searcher.doc, doc_id)
            modified: bool = bool(doc[MODIFIED][0])
            if modified and not force:
                classification: str = doc[CLASSIFICATION][0]
                file.update({CLASSIFICATION: classification})
                file.update({MODIFIED: True})
            if modified and force:
                file.update({MODIFIED: True})

        await to_thread(self.writer.delete_documents_by_query, Query.term_query(self.index.schema, UNIQUE_POINTER, unique_pointer))
        extension: str = file.get("file_type", "")
        file.update({IS_DOCUMENT: extension in self.documents_only_extension})
        await to_thread(self.writer.add_json, json.dumps(file))

    async def remove_file(self, pointer: str) -> None:
        """Remove a file from the index.

        Args:
            pointer: unique pointer.
        """

        async with self.open_writer():
            await to_thread(self.writer.delete_documents, UNIQUE_POINTER, pointer)
            dms_info(f"Removed {pointer} from index.")
