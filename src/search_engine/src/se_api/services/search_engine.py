"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import json
from os import listdir, mkdir, path, remove

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
    categories: list[str]
    writer: IndexWriter | None
    index_path: str
    documents_only_extension: list

    def __init__(self) -> None:
        """Constructor"""
        self.index_path = read_env_variable("SEARCHENG_WORKING_DIRECTORY").rstrip("/") + "/index"
        self.categories = ["is_document"]
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
        if fields is not None:
            self.categories.extend(fields)
        schema_builder = SchemaBuilder()
        for category in self.categories:
            dms_info(f"added field {category}")
            if category == "unique_pointer":
                schema_builder.add_text_field(category, stored=True, tokenizer_name="raw")
            elif category == "is_document":
                schema_builder.add_boolean_field(category, stored=True, indexed=True)
            else:
                schema_builder.add_text_field(category, stored=True)
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

    def reset(self) -> None:
        """Reset the search engine."""
        for file in listdir(self.index_path):
            remove(f"{self.index_path}/{file}")
        self.init(None)

    def query_files(self, content: dict[str, str], count: int) -> list[str]:
        """Query through the files in the index.

        Args:

        Returns:
            List of file pointers with matching content.

        Raises:
            SeAPIException: Potential formatting errors.
        """

        sub_queries: list[tuple] = []
        for field, value in content.items():
            try:
                if field == "documents_only":
                    field = "is_document"
                sub_queries.append((
                    Occur.Must,
                    self.index.parse_query(value, [field])
                ))
            except ValueError:
                dms_warning(f"Failed to create query: {value} for field: {field}")
            except TypeError:
                dms_warning(f"Value is of wrong type, expected string got {type(value)}: {value}")

        query: Query = Query.boolean_query(sub_queries)

        searcher: Searcher = self.index.searcher()
        result: SearchResult = searcher.search(query, count)
        pointers: list[str] = []
        for _, doc_id in result.hits:
            doc: Document = searcher.doc(doc_id)
            unique_poinet = doc["unique_pointer"][0]
            pointers.append(unique_poinet)

        return pointers

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
        unique_pointer: str | None = file.get("unique_pointer")
        if unique_pointer is None:
            dms_warning(f"File is missing unique pointer: {file.update({"content": ""})}.")
            return
        self.writer.delete_documents("unique_pointer", "".join(unique_pointer))
        extension: str = file.get("file_type", "")
        file.update({"is_document": extension in self.documents_only_extension})
        self.writer.add_json(json.dumps(file))

    def remove_file(self, pointer: str) -> None:
        """Remove a file from the index.

        Args:
            pointer: unique pointer.
        """

        writer: IndexWriter = self.index.writer()
        writer.delete_documents("unique_pointer", pointer)
        writer.commit()
        writer.wait_merging_threads()
        dms_info(f"Removed {pointer} from index.")
        self.index.reload()
