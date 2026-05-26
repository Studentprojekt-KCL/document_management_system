from asyncio import Lock
from unittest import IsolatedAsyncioTestCase, mock

from tantivy import Index, SchemaBuilder

from se_api.constants import CLASSIFICATION, CONTENT, IS_DOCUMENT, MODIFIED, UNIQUE_POINTER
from se_api.services.search_engine import SearchEngine


class TestSearchEngine(IsolatedAsyncioTestCase):
    FILE_BASE: dict = {
        UNIQUE_POINTER: "pointer-1",
        CONTENT: "content-1",
        MODIFIED: False,
        CLASSIFICATION: "class-1",
        IS_DOCUMENT: False,
    }

    FILE_CONTENT_MODIFIED: dict = {
        UNIQUE_POINTER: "pointer-1",
        CONTENT: "content-2",
        MODIFIED: False,
        CLASSIFICATION: "class-1",
        IS_DOCUMENT: False,
    }

    FILE_MODIFIED: dict = {
        UNIQUE_POINTER: "pointer-1",
        CONTENT: "content-2",
        MODIFIED: True,
        CLASSIFICATION: "class-2",
        IS_DOCUMENT: False,
    }

    CATEGORIES: set = {UNIQUE_POINTER, CONTENT, MODIFIED, IS_DOCUMENT, CLASSIFICATION}
    DOCUMENTS_ONLY_EXTENSION: list = [".txt", ".md"]

    @mock.patch("se_api.services.search_engine.SearchEngine.__init__", return_value=None)
    def setUp(self, _):
        self.instance = SearchEngine()
        self.instance.categories = self.CATEGORIES

        schema_builder = SchemaBuilder()
        schema_builder.add_text_field(UNIQUE_POINTER, stored=True, tokenizer_name="raw")
        schema_builder.add_text_field(CONTENT, stored=True)
        schema_builder.add_boolean_field(MODIFIED, stored=True)
        schema_builder.add_boolean_field(IS_DOCUMENT, stored=True)
        schema_builder.add_text_field(CLASSIFICATION, stored=True)
        schema = schema_builder.build()
        self.instance.documents_only_extension = self.DOCUMENTS_ONLY_EXTENSION
        self.instance.index = Index(schema)
        self.instance.writer = self.instance.index.writer()
        self.instance.writer_lock = Lock()

    async def test_add_file(self):
        async with self.instance.open_writer():
            await self.instance.add_file(self.FILE_BASE)
        file = self.instance.grab_file("pointer-1")
        assert file == self.FILE_BASE

    async def test_overwriter_file(self):
        async with self.instance.open_writer():
            await self.instance.add_file(self.FILE_BASE)
        async with self.instance.open_writer():
            await self.instance.add_file(self.FILE_CONTENT_MODIFIED)
        file = self.instance.grab_file("pointer-1")
        assert file == self.FILE_CONTENT_MODIFIED

    async def test_overwrite_modified(self):
        async with self.instance.open_writer():
            await self.instance.add_file(self.FILE_MODIFIED)
        async with self.instance.open_writer():
            await self.instance.add_file(self.FILE_BASE)
        file = self.instance.grab_file("pointer-1")
        assert file == {
            UNIQUE_POINTER: "pointer-1",
            CONTENT: "content-1",
            MODIFIED: True,
            CLASSIFICATION: "class-2",
            IS_DOCUMENT: False,
        }

    async def test_force_overwrite_modified(self):
        async with self.instance.open_writer():
            await self.instance.add_file(self.FILE_MODIFIED)
        async with self.instance.open_writer():
            await self.instance.add_file(self.FILE_BASE, force=True)
        file = self.instance.grab_file("pointer-1")
        assert file == {
            UNIQUE_POINTER: "pointer-1",
            CONTENT: "content-1",
            MODIFIED: True,
            CLASSIFICATION: "class-1",
            IS_DOCUMENT: False,
        }

    async def test_set_classification(self):
        async with self.instance.open_writer():
            await self.instance.add_file(self.FILE_BASE)
        await self.instance.set_classification("pointer-1", "class-3")

        file = self.instance.grab_file("pointer-1")
        assert file == {
            UNIQUE_POINTER: "pointer-1",
            CONTENT: "content-1",
            MODIFIED: True,
            CLASSIFICATION: "class-3",
            IS_DOCUMENT: False,
        }

    async def test_remove_file(self):
        async with self.instance.open_writer():
            await self.instance.add_file(self.FILE_BASE)
        await self.instance.remove_file("pointer-1")
        file = self.instance.grab_file("pointer-1")
        assert file == {}
