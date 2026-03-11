"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import base64
from tantivy import (
    Document,
    Index,
    IndexWriter,
    Query,
    SchemaBuilder,
    SearchResult,
    Searcher,
)

from se_api.exceptions import SeAPIException
from se_api.models import File


class SearchEngine:
    """Search engine service

    Attributes:
        index: The built index from the gathered files.
    """

    index: Index

    def __init__(self) -> None:
        schema_builder = SchemaBuilder()
        _ = schema_builder.add_text_field("name", stored=True)
        _ = schema_builder.add_text_field("unique_pointer", stored=True)
        _ = schema_builder.add_text_field("edited", stored=True)
        _ = schema_builder.add_text_field("type", stored=True)
        _ = schema_builder.add_text_field("content", stored=True)
        _ = schema_builder.add_integer_field("size", stored=True)
        schema = schema_builder.build()

        # Memory only
        self.index = Index(schema)

    def query_files(self, q: str, k: int = 50) -> list[str]:
        """Query through the files in the index.

        Args:
            q: The query to perform.
            k: Maximum number of results.

        Returns:
            List of file pointers with matching content.

        Raises:
            SeAPIException: Potential formatting errors.
        """

        searcher: Searcher = self.index.searcher()
        query: Query = self.index.parse_query(q, ["name", "content", "unique_pointer"])
        result: SearchResult = searcher.search(query, k)
        pointers: list[str] = []
        for _, doc_id in result.hits:
            doc: Document = searcher.doc(doc_id)
            unique_poinet = doc["unique_pointer"][0]

            if not isinstance(unique_poinet, str):
                raise SeAPIException("")

            pointers.append(unique_poinet)

        return pointers

    def add_file(self, file: File) -> None:
        """Add a file to the index.

        Args:
            file: the file to add.
        """
        writer: IndexWriter = self.index.writer()
        content_byte = base64.b64decode(file.content)
        content = content_byte.decode("utf-8")
        _ = writer.add_document(
            Document(
                name=file.metadata.name if file.metadata.name is not None else "",
                unique_pointer=file.metadata.unique_pointer,
                edited=file.metadata.edited.isoformat() if file.metadata.edited is not None else "",
                type=file.metadata.type if file.metadata.type is not None else "",
                size=file.metadata.size if file.metadata.size is not None else "",
                content=content,
            )
        )
        _ = writer.commit()
        writer.wait_merging_threads()
        self.index.reload()

    def add_files(self, files: list[File]) -> None:
        """Add a list of files to the index.

        Args:
            files: list of files.
        """

        writer: IndexWriter = self.index.writer()
        for file in files:
            content_byte = base64.b64decode(file.content)
            content = content_byte.decode("utf-8", "ignore")
            _ = writer.add_document(
                Document(
                    name=file.metadata.name if file.metadata.name is not None else "",
                    unique_pointer=file.metadata.unique_pointer,
                    edited=file.metadata.edited.isoformat() if file.metadata.edited is not None else "",
                    type=file.metadata.type if file.metadata.type is not None else "",
                    size=file.metadata.size if file.metadata.size is not None else "",
                    content=content,
                )
            )
        _ = writer.commit()
        writer.wait_merging_threads()
        self.index.reload()
