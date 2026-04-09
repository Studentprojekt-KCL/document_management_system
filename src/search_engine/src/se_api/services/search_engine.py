"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import base64
import json
from dmis_logger import dms_info, dms_warning
from tantivy import (
    Document,
    Index,
    IndexWriter,
    SchemaBuilder,
    SearchResult,
    Searcher,
)


class SearchEngine:
    """Search engine service

    Attributes:
        index: The built index from the gathered files.
    """

    index: Index
    categories: list[str]

    def __init__(self) -> None:
        self.categories = ["unique_pointer", "content"]
        self.rebuild()

    def rebuild(self) -> None:
        """Rebuild the index schema with the saved categories."""
        dms_info(f"Rebuilding schema, new set: {self.categories}.")
        schema_builder = SchemaBuilder()
        for category in self.categories:
            _ = schema_builder.add_text_field(category, stored=True)
        schema = schema_builder.build()
        self.index = Index(schema)

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

    def add_files(self, files: list) -> None:
        """Add a list of files to the index.

        Args:
            files: list of files.
        """

        writer: IndexWriter = self.index.writer()
        for file in files:
            flat_file = self._flatten_dict(file)
            content = flat_file.get("content")
            unique_pointer = flat_file.get("unique_pointer")

            if content is None:
                dms_warning("File is missing content.")
                continue
            if unique_pointer is None:
                dms_warning("File is missing unique pointer.")
                continue

            content_bytes: bytes = base64.b64decode(content)
            content = content_bytes.decode("utf-8")
            flat_file["content"] = content

            _ = writer.add_json(json.dumps(flat_file))

        _ = writer.commit()
        writer.wait_merging_threads()

        self.index.reload()

    def _flatten_dict(self, d: dict) -> dict:
        flat: dict = {}

        for key, val in d.items():
            if isinstance(val, dict):
                flat.update(self._flatten_dict(val))
            else:
                flat.update({key: str(val)})

        return flat
