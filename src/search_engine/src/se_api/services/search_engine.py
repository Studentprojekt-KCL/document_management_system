"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import json
from os import listdir, mkdir, path, remove

from httpx import get
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
    writer: IndexWriter | None
    index_path: str
    documents_only_extension: list

    CLASSIFICATION: str = "classification"
    IS_DOCUMENT: str = "is_document"
    MODIFIED: str = "modified"
    UNIQUE_POINTER: str = "unique_pointer"

    BOOLEAN_CATEGORIES: set[str] = {IS_DOCUMENT, MODIFIED}
    RAW_CATEGORIES: set[str] = {UNIQUE_POINTER, CLASSIFICATION}

    def __init__(self) -> None:
        """Constructor"""
        self.index_path = read_env_variable("SEARCHENG_WORKING_DIRECTORY", required=True).rstrip("/") + "/index" # type: ignore[attr-defined]
        self.categories = self.BOOLEAN_CATEGORIES.copy()
        self.categories.union(self.RAW_CATEGORIES.copy())
        extentions = get_documents_only_rescource()
        self.documents_only_extension = []
        for extention in extentions:
            self.documents_only_extension.extend(extention.get("extension", []))
        self.writer = None

    def init(self, fields: list[str] | None) -> None:
        """Initialize the index schema with the saved categories."""
        if not path.exists(self.index_path):
            mkdir(self.index_path)
        if not path.isdir(self.index_path):
            dms_error(f"{self.index_path} is not a directory.")
            return
        self.categories = self.BOOLEAN_CATEGORIES.copy()
        self.categories.union(self.RAW_CATEGORIES.copy())
        if fields is not None:
            for field in fields:
                self.categories.add(field)
        schema_builder = SchemaBuilder()
        for category in self.categories:
            if category in self.RAW_CATEGORIES:
                schema_builder.add_text_field(category, stored=True, tokenizer_name="raw")
            elif category in self.BOOLEAN_CATEGORIES:
                schema_builder.add_boolean_field(category, stored=True, indexed=True)
            else:
                schema_builder.add_text_field(category, stored=True)
            dms_info(f"added field {category}")
        schema = schema_builder.build()
        try:
            self.index = Index(schema, path=self.index_path)
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
        result = searcher.search(Query.term_query(self.index.schema, field_name=self.UNIQUE_POINTER, field_value=unique_pointer))
        if not result.hits:
            return None
        doc_address = result.hits[0][1]
        doc = searcher.doc(doc_address)
        file: dict = {}
        for category in self.categories:
            file.update({category: doc[category][0]}) 
        file.update({self.CLASSIFICATION: classification})
        file.update({self.MODIFIED: True})
        self.open_writer()
        self.add_file(file)
        self.close_writer()
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
                    (Occur.Must, self.index.parse_query(value, [field if field != "documents_only" else self.IS_DOCUMENT]))
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
            unique_pointer = doc[self.UNIQUE_POINTER][0]
            classification = doc[self.UNIQUE_POINTER][0]
            classifications.update({unique_pointer: classification})
            pointers.append(unique_pointer)

        return (pointers, classifications)

    def find_matching(self, unique_pointer) -> None:
        searcher = self.index.searcher()
        result = searcher.search(Query.term_query(self.index.schema, field_name=self.UNIQUE_POINTER, field_value=unique_pointer))
        doc_address = result.hits[0][1]
        result = searcher.search(Query.more_like_this_query(doc_address))
        for score, doc_id in result.hits:
            doc: Document = searcher.doc(doc_id)
            unique_pointer = doc[self.CLASSIFICATION][0]
            print(f"{score}: {unique_pointer}")

    def open_writer(self) -> None:
        """Init index writer."""
        if self.writer is not None:
            return
        self.writer = self.index.writer()

    def close_writer(self) -> None:
        """Close the writer."""
        if self.writer is None:
            return
        self.writer.commit()
        self.writer.wait_merging_threads()
        self.writer = None

    def add_file(self, file: dict) -> None:
        """Add file to index.

        Requiers init call before and after.

        Args:
            file: file dict
        """

        if self.writer is None:
            return
        unique_pointer: str | None = file.get(self.UNIQUE_POINTER)
        if unique_pointer is None:
            dms_warning(f"File is missing unique pointer: {file.update({"content": ""})}.")
            return
        searcher: Searcher = self.index.searcher()
        matches = searcher.search(Query.term_query(self.index.schema, self.UNIQUE_POINTER, unique_pointer))
        if matches.hits:
            doc_id = matches.hits[0][1]
            modified: bool = bool(searcher.doc(doc_id)[self.MODIFIED][0])
            if modified:
                classification: str = searcher.doc(doc_id)[self.CLASSIFICATION][0] 
                file.update({self.CLASSIFICATION: classification})
        else:
            file.update({self.MODIFIED: False})
        self.writer.delete_documents(self.UNIQUE_POINTER, "".join(unique_pointer))
        extension: str = file.get("file_type", "")
        file.update({self.IS_DOCUMENT: extension in self.documents_only_extension})
        self.writer.add_json(json.dumps(file))

    def remove_file(self, pointer: str) -> None:
        """Remove a file from the index.

        Args:
            pointer: unique pointer.
        """

        writer: IndexWriter = self.index.writer()
        writer.delete_documents(self.UNIQUE_POINTER, pointer)
        writer.commit()
        writer.wait_merging_threads()
        dms_info(f"Removed {pointer} from index.")
        self.index.reload()
