"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import base64
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

from se_api.exceptions import SeAPIException
from se_api.models.file import File
from se_api.models import query, metadata
from se_api import models


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

    def query_files(self, q: query.Query, k: int = 50) -> list[str]:
        """Query through the files in the index.

        Args:
            q: The query to perform.
            k: Maximum number of results.

        Returns:
            List of file pointers with matching content.

        Raises:
            SeAPIException: Potential formatting errors.
        """

        queries: list[Query] = []

        content: Query = Query.boost_query(self.index.parse_query(q.query, ["content"]), 1.0) if isinstance(q.query, str) else Query.empty_query()

        queries.append(content)

        if isinstance(q.metadata, metadata.Metadata):
            queries.append(Query.boost_query(self.index.parse_query(q.metadata.name, ["name"]), 3.0) if isinstance(q.metadata.name, str) else Query.empty_query())
            queries.append(Query.boost_query(self.index.parse_query(q.metadata.edited, ["edited"]), 1.0) if isinstance(q.metadata.edited, str) else Query.empty_query())
            queries.append(Query.boost_query(self.index.parse_query(q.metadata.type, ["type"]), 1.0) if isinstance(q.metadata.type, str) else Query.empty_query())
            queries.append(Query.boost_query(self.index.parse_query(q.metadata.size, ["size"]), 1.0) if isinstance(q.metadata.size, str) else Query.empty_query())

        query = Query.boolean_query([(Occur.Must, Query.disjunction_max_query(queries, 0.3))])

        searcher: Searcher = self.index.searcher()
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
