"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import json
from types import TracebackType
from tantivy import (
    Document,
    Index,
    IndexWriter,
    SchemaBuilder,
    SearchResult,
    Searcher,
    TextAnalyzer,
    TextAnalyzerBuilder,
    Tokenizer,
)

from shared_functions.dmis_logger import dms_info, dms_warning


class SearchEngine:
    """Search engine service

    Attributes:
        index: The built index from the gathered files.
    """

    index: Index
    categories: list[str]
    writer: IndexWriter | None

    def __init__(self) -> None:
        self.categories = ["unique_pointer", "content"]
        self.writer = None
        self.rebuild()

    def rebuild(self) -> None:
        """Rebuild the index schema with the saved categories."""
        dms_info(f"Rebuilding schema, new set: {self.categories}.")
        schema_builder = SchemaBuilder()
        for category in self.categories:
            if category == "unique_pointer":
                schema_builder.add_text_field(category, stored=True, tokenizer_name="raw")
            else:
                schema_builder.add_text_field(category, stored=True)
        schema = schema_builder.build()
        self.index = Index(schema)

        rag: TextAnalyzer = TextAnalyzerBuilder(Tokenizer.regex(r"([A-Z][a-z][0-9])+")).build()
        self.index.register_tokenizer("se-rag", rag)

    def have_new_category(self, categories: dict) -> bool:
        """Check if there is an apsent category.

        Args:
            categories: the dict containing the categories.

        Returns:
        True if there are new ones, else False
        """

        new: bool = False
        for key in categories:
            category = categories.get(key)
            if isinstance(category, dict):
                new = new or self.have_new_category(category)
            elif key not in self.categories:
                new = True
                self.categories.append(key)

        return new

    def query_files(self, q: str, k: int) -> list[str]:
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
        for _, doc_id in result.hits:
            doc: Document = searcher.doc(doc_id)
            unique_poinet = doc["unique_pointer"][0]
            pointers.append(unique_poinet)

        return pointers

    def __enter__(self) -> SearchEngine:
        """Init index writer."""
        if self.writer is not None:
            return self
        self.writer = self.index.writer()
        return self

    def __exit__(self, _exception_type: BaseException, _exception_value: BaseException, _traceback: TracebackType) -> None:
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
            dms_warning("File is missing unique pointer.")
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
