from unittest import IsolatedAsyncioTestCase, mock

from se_api.services.connector import Connector


class TestConnector(IsolatedAsyncioTestCase):
    @mock.patch("se_api.services.connector.Connector.__init__", return_value=None)
    def setUp(self, _):
        self.instance = Connector()
        self.instance.index_needed_bool = "/index_needed_bool"
        self.instance.url_files_to_index = "/files_to_index"
        self.instance.url_get_files = "/get_files"
        self.instance.subdata = None

    def test_reset(self):
        self.instance.subdata = ""
        self.instance.reset()
        assert self.instance.subdata is None

    # ==== GET_FILE_POINTERS ====

    @mock.patch("se_api.services.connector.Connector._get_reindex_needed")
    async def test_reindex_needed(self, mock_get):
        mock_get.return_value = {"index_needed": True}
        result = await self.instance.reindex_needed()
        assert result == True

    @mock.patch("se_api.services.connector.Connector._get_reindex_needed")
    async def test_reindex_not_needed(self, mock_get):
        mock_get.return_value = {"index_needed": False}
        result = await self.instance.reindex_needed()
        assert result == False

    # ==== FETCH_FILES_FROM_POINTERS ====

    @mock.patch("se_api.services.connector.Connector._get_file_from_pointers")
    async def test_fetch_files_dict(self, mock_get_file_from_pointer):
        mock_get_file_from_pointer.return_value = {}
        result = await self.instance.fetch_files(["pointer"])
        assert result == []

    @mock.patch("se_api.services.connector.Connector._get_file_from_pointers")
    async def test_fetch_files_list(self, mock_get_file_from_pointer):
        mock_get_file_from_pointer.return_value = []
        result = await self.instance.fetch_files(["pointer"])
        assert result == []

    @mock.patch("se_api.services.connector.Connector._get_file_from_pointers")
    async def test_fetch_files_empty(self, mock_get_file_from_pointer):
        mock_get_file_from_pointer.return_value = None
        result = await self.instance.fetch_files(["pointer"])
        assert result == []

    @mock.patch("se_api.services.connector.Connector._get_file_from_pointers")
    async def test_fetch_files_full(self, mock_get_file_from_pointer):
        mock_get_file_from_pointer.return_value = [{"item1": "item", "item2": "item"}]
        result = await self.instance.fetch_files(["pointer"])
        assert result == [{"item1": "item", "item2": "item"}]
