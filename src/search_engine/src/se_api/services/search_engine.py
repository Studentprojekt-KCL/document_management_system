"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from collections.abc import Generator
from contextlib import contextmanager
import json
from os import listdir, mkdir, path, remove
from threading import Lock

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

    def __init__(self) -> None:
        """Constructor"""
        self.index_path = read_env_variable("SEARCHENG_WORKING_DIRECTORY", required=True).rstrip("/") + "/index"  # type: ignore
        extentions = get_documents_only_rescource()
        self.documents_only_extension = []
        for extention in extentions:
            self.documents_only_extension.extend(extention.get("extension", []))
        self.writer = None
        self.writer_lock = Lock()

    def init(self, fields: list[str] | None) -> None:
        """Initialize the index schema with the saved categories."""
        if not path.exists(self.index_path):
            mkdir(self.index_path)
        if not path.isdir(self.index_path):
            dms_error(f"{self.index_path} is not a directory.")
            return
        self.categories = BOOLEAN_CATEGORIES
        self.categories = self.categories.union(RAW_CATEGORIES)
        self.categories = self.categories.union(COOKED_CATEGORIES)
        if fields is not None:
            for field in fields:
                self.categories.add(field)
        categories = sorted(self.categories)
        schema_builder = SchemaBuilder()
        for category in categories:
            if category in RAW_CATEGORIES:
                schema_builder.add_text_field(category, stored=True, tokenizer_name="raw")
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
            except ValueError:
                dms_error(f"Failed loading index directory, path: {self.index_path}.")

    def reset(self, fields: list[str] | None) -> None:
        """Reset the search engine."""
        for file in listdir(self.index_path):
            remove(f"{self.index_path}/{file}")
        self.init(fields)

    def set_classification(self, unique_pointer: str, classification: str) -> tuple[str, str] | None:
        """Set the classification of a file in the index.

        Args:
            unique_pointer: pointer for the file.
            classification: new classification.
        """
        searcher = self.index.searcher()
        result = searcher.search(Query.term_query(self.index.schema, field_name=UNIQUE_POINTER, field_value=unique_pointer))
        if not result.hits:
            return None
        doc_address = result.hits[0][1]
        doc = searcher.doc(doc_address)
        file: dict = {}
        for category in self.categories:
            file.update({category: doc[category][0]})
        file.update({CLASSIFICATION: classification})
        file.update({MODIFIED: True})
        with self.open_writer() as writer:
            self.add_file(file, writer)
        return (unique_pointer, classification)

    def query_files(self, content: dict[str, str], count: int) -> tuple[list[str], dict[str, str]]:
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
                dms_warning(f"Failed to create query: {value} for field: {field}")
            except TypeError:
                dms_warning(f"Value is of wrong type, expected string got {type(value)}: {value}")

        query: Query = Query.boolean_query(sub_queries)

        searcher: Searcher = self.index.searcher()
        result: SearchResult = searcher.search(query, count)
        pointers: list[str] = []
        classifications: dict[str, str] = {}
        for _, doc_id in result.hits:
            doc: Document = searcher.doc(doc_id)
            unique_pointer = doc[UNIQUE_POINTER][0]
            classification = doc[CLASSIFICATION][0]
            classifications.update({unique_pointer: classification})
            pointers.append(unique_pointer)

        return (pointers, classifications)

    def find_matching(self, unique_pointer: str, count: int | None) -> dict:
        """Search for matching files.

        Args:
            unique_pointer: file to match with.
            count: number of wanted results.
        Returns: unique pointers and their score.
        """
        if count is not None and count < 0:
            dms_warning(f"Recived count below 0 as an argument in 'find_matching', {count}")
            return {}

        matching: dict = {}
        searcher = self.index.searcher()
        result = searcher.search(Query.term_query(self.index.schema, field_name=UNIQUE_POINTER, field_value=unique_pointer))
        if not result.hits:
            return {}
        doc_address = result.hits[0][1]
        result = searcher.search(Query.more_like_this_query(doc_address))
        original_score: int | None = None
        for score, doc_id in result.hits:
            if original_score is None:
                original_score = score
            doc: Document = searcher.doc(doc_id)
            unique_pointer = doc[UNIQUE_POINTER][0]
            matching.update({unique_pointer: score / original_score})
            if count is not None and len(matching) == count:
                break
        return matching

    @contextmanager
    def open_writer(self) -> Generator[IndexWriter]:
        """Init index writer."""
        self.writer_lock.acquire()
        writer: IndexWriter = self.index.writer()
        yield writer
        writer.commit()
        writer.wait_merging_threads()
        self.writer_lock.release()

    def grab_file(self, unique_pointer: str) -> dict:
        """Grab a file from the index.

        Args:
            unique_pointer: the file pointer.
        Returns: file dict.
        """
        file: dict = {}
        searcher: Searcher = self.index.searcher()
        matches = searcher.search(Query.term_query(self.index.schema, UNIQUE_POINTER, unique_pointer))
        if matches.hits:
            doc_id = matches.hits[0][1]
            doc = searcher.doc(doc_id)
            for category in self.categories:
                try:
                    file[category] = doc[category][0]
                except IndexError:
                    file[category] = "N/A"
            return file
        dms_warning(f"Failed to fetch content from index: {unique_pointer}")
        return file

    def add_file(self, file: dict, writer: IndexWriter) -> None:
        """Add file to index.

        Requiers init call before and after.

        Args:
            file: file dict
        """

        unique_pointer: str | None = file.get(UNIQUE_POINTER)
        if unique_pointer is None:
            dms_warning(f"File is missing unique pointer: {file.update({CONTENT: ""})}.")
            return
        searcher: Searcher = self.index.searcher()
        matches = searcher.search(Query.term_query(self.index.schema, UNIQUE_POINTER, unique_pointer))
        if matches.hits:
            doc_id = matches.hits[0][1]
            doc = searcher.doc(doc_id)
            modified: bool = bool(doc[MODIFIED][0])
            if modified:
                classification: str = doc[CLASSIFICATION][0]
                file.update({CLASSIFICATION: classification})
                file.update({MODIFIED: True})
            else:
                file.update({MODIFIED: False})
        else:
            file.update({MODIFIED: False})
        writer.delete_documents_by_query(Query.term_query(self.index.schema, UNIQUE_POINTER, unique_pointer))
        extension: str = file.get("file_type", "")
        file.update({IS_DOCUMENT: extension in self.documents_only_extension})
        writer.add_json(json.dumps(file))

    def remove_file(self, pointer: str) -> None:
        """Remove a file from the index.

        Args:
            pointer: unique pointer.
        """

        with self.open_writer() as writer:
            writer.delete_documents(UNIQUE_POINTER, pointer)
            writer.commit()
            writer.wait_merging_threads()
            dms_info(f"Removed {pointer} from index.")
