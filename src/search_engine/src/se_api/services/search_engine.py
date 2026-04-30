"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import json
from os import listdir, mkdir, path, remove

from tantivy import (
    Document,
    Index,
    IndexWriter,
    Query,
    SchemaBuilder,
    SearchResult,
    Searcher,
)

from shared_functions.initialisation_tools import read_env_variable
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

    def __init__(self) -> None:
        """Constructor"""
        self.index_path = read_env_variable("SEARCHENG_WORKING_DIRECTORY", required=True).rstrip("/") + "/index" # type: ignore[attr-defined]
        self.categories = ["unique_pointer", "content", "classification"]
        self.writer = None

    def init(self) -> None:
        """Initialize the index schema with the saved categories."""
        if not path.exists(self.index_path):
            mkdir(self.index_path)
        if not path.isdir(self.index_path):
            dms_error(f"{self.index_path} is not a directory.")
        schema_builder = SchemaBuilder()
        for category in self.categories:
            if category == "unique_pointer":
                schema_builder.add_text_field(category, stored=True, tokenizer_name="raw")
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
        self.init()

    def set_classification(self, unique_pointer: str, classification: str) -> dict[str, str]:
        """Set the classification of a file in the index.

        Args:
            unique_pointer: pointer for the file.
            classification: new classification.
        """
        searcher = self.index.searcher()
        result = searcher.search(Query.term_query(self.index.schema, field_name="unique_pointer", field_value=unique_pointer))
        doc_address = result.hits[0][1]
        doc = searcher.doc(doc_address)
        file: dict = {}
        for category in self.categories:
            file.update({category: doc[category][0]}) 
        file.update({"classification": classification})
        self.add_file(file)
        file.pop("contnet")
        return file

    def query_files(self, q: str, k: int) -> tuple[list[str], dict[str, str]]:
        """Query through the files in the index.

        Args:
            q: The query to perform.
            k: Maximum number of results.

        Returns:
            List of file pointers with matching content.

        Raises:
            SeAPIException: Potential formatting errors.
        """

        query = self.index.parse_query(q, self.categories)

        searcher: Searcher = self.index.searcher()
        result: SearchResult = searcher.search(query, k)
        pointers: list[str] = []
        classifications: dict[str, str] = {}
        for _, doc_id in result.hits:
            doc: Document = searcher.doc(doc_id)
            unique_pointer = doc["unique_pointer"][0]
            classification = doc["classification"][0]
            classifications.update({unique_pointer: classification})
            pointers.append(unique_pointer)

        return (pointers, classifications)

    def find_matching(self, unique_pointer) -> None:
        searcher = self.index.searcher()
        result = searcher.search(Query.term_query(self.index.schema, field_name="unique_pointer", field_value=unique_pointer))
        doc_address = result.hits[0][1]
        result = searcher.search(Query.more_like_this_query(doc_address))
        for score, doc_id in result.hits:
            doc: Document = searcher.doc(doc_id)
            unique_pointer = doc["unique_pointer"][0]
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
        unique_pointer: str | None = file.get("unique_pointer")
        if unique_pointer is None:
            dms_warning(f"File is missing unique pointer: {file.update({"content": ""})}.")
            return
        self.writer.delete_documents("unique_pointer", "".join(unique_pointer))

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
