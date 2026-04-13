from unittest import TestCase, mock
from se_api.services.connector import Connector


class TestConnector(TestCase):
    @mock.patch("se_api.services.connector.Connector.__init__", return_value=None)
    def setUp(self, _):
        self.instance = Connector()
        self.instance.address = ""
        self.instance.index_needed_bool = "/index_needed_bool"
        self.instance.url_files_to_index = "/files_to_index"
        self.instance.url_get_files = "/get_files"
        self.instance.subdata = None

    def test_reset(self):
        self.instance.subdata = ""
        self.instance.reset()
        assert self.instance.subdata is None

    def reindex_side_effect(self):
        if self.instance.subdata == None:
            return {"index_needed": True}
        return {"index_needed": False}

    # ==== GET_FILE_POINTERS ====

    @mock.patch("se_api.services.connector.get")
    def test_reindex_needed(self, mock_get):
        self.instance.subdata = None
        mock_get.return_value.json.side_effect = self.reindex_side_effect
        result = self.instance.reindex_needed()
        assert result == True

    @mock.patch("se_api.services.connector.get")
    def test_reindex_not_needed(self, mock_get):
        self.instance.subdata = "amVzcGVy"
        mock_get.return_value.json.side_effect = self.reindex_side_effect
        result = self.instance.reindex_needed()
        assert result == False

    # ==== FETCH_FILES_FROM_POINTERS ====

    @mock.patch("se_api.services.connector.Connector._get_file_from_pointer")
    def test_fetch_files_dict(self, mock_get_file_from_pointer):
        mock_get_file_from_pointer.return_value = {}
        result = self.instance.fetch_files(["pointer"])
        assert result == []

    @mock.patch("se_api.services.connector.Connector._get_file_from_pointer")
    def test_fetch_files_list(self, mock_get_file_from_pointer):
        mock_get_file_from_pointer.return_value = []
        result = self.instance.fetch_files(["pointer"])
        assert result == []

    @mock.patch("se_api.services.connector.Connector._get_file_from_pointer")
    def test_fetch_files_empty(self, mock_get_file_from_pointer):
        mock_get_file_from_pointer.return_value = None
        result = self.instance.fetch_files(["pointer"])
        assert result == []

    @mock.patch("se_api.services.connector.Connector._get_file_from_pointer")
    def test_fetch_files_full(self, mock_get_file_from_pointer):
        mock_get_file_from_pointer.return_value = [{"item1": "item", "item2": "item"}]
        result = self.instance.fetch_files(["pointer"])
        assert result == [{"item1": "item", "item2": "item"}]

    # ==== GET_FILE ====

    @mock.patch("se_api.services.connector.Connector._files_to_index")
    def test_get_files_empty_url(self, mock_file_to_index):
        mock_file_to_index.return_value = None
        result = self.instance.get_files()
        assert result == []

    @mock.patch("se_api.services.connector.Connector._get_files_from_url")
    @mock.patch("se_api.services.connector.Connector._files_to_index")
    def test_get_files_none(self, mock_file_to_index, mock_get_file_from_url):
        mock_file_to_index.return_value = ""
        mock_get_file_from_url.return_value = None
        result = self.instance.get_files()
        assert result == []

    @mock.patch("se_api.services.connector.Connector._get_files_from_url")
    @mock.patch("se_api.services.connector.Connector._files_to_index")
    def test_get_files_list(self, mock_file_to_index, mock_get_file_from_url):
        mock_file_to_index.return_value = ""
        mock_get_file_from_url.return_value = []
        result = self.instance.get_files()
        assert result == []

    @mock.patch("se_api.services.connector.Connector._get_files_from_url")
    @mock.patch("se_api.services.connector.Connector._files_to_index")
    def test_get_files_valid(self, mock_file_to_index, mock_get_files_from_url):
        mock_file_to_index.return_value = ""
        mock_get_files_from_url.return_value = {"files": ["file1", "file2"], "subdata": "subdata"}
        result = self.instance.get_files()
        assert result == ["file1", "file2"]
        assert self.instance.subdata == "subdata"

    @mock.patch("se_api.services.connector.Connector._get_files_from_url")
    @mock.patch("se_api.services.connector.Connector._files_to_index")
    def test_get_files_data(self, mock_file_to_index, mock_get_files_from_url):
        mock_file_to_index.return_value = ""
        mock_get_files_from_url.return_value = {"subdata": "subdata"}
        result = self.instance.get_files()
        assert result == []
        assert self.instance.subdata is None

    @mock.patch("se_api.services.connector.Connector._get_files_from_url")
    @mock.patch("se_api.services.connector.Connector._files_to_index")
    def test_get_files_subdata(self, mock_file_to_index, mock_get_files_from_url):
        mock_file_to_index.return_value = ""
        mock_get_files_from_url.return_value = {"files": ["file1", "file2"]}
        result = self.instance.get_files()
        assert result == ["file1", "file2"]
        assert self.instance.subdata is None

    # ==== _FILES_TO_INDEX ====

    @mock.patch("se_api.services.connector.Connector._get_file_to_index")
    def test__files_to_index_none(self, mock_get_file_to_index):
        mock_get_file_to_index.return_value = None
        result = self.instance._files_to_index()
        assert result is None

    @mock.patch("se_api.services.connector.Connector._get_file_to_index")
    def test__files_to_index_dict(self, mock_get_file_to_index):
        mock_get_file_to_index.return_value = {}
        result = self.instance._files_to_index()
        assert result is None
        assert self.instance.subdata is None

    @mock.patch("se_api.services.connector.Connector._get_file_to_index")
    def test__files_to_index_list(self, mock_get_file_to_index):
        mock_get_file_to_index.return_value = []
        result = self.instance._files_to_index()
        assert result is None
        assert self.instance.subdata is None

    @mock.patch("se_api.services.connector.Connector._get_file_to_index")
    def test__files_to_index_file_url(self, mock_get_file_to_index):
        mock_get_file_to_index.return_value = {"file_url": "file_url"}
        result = self.instance._files_to_index()
        assert result == "file_url"
        assert self.instance.subdata is None

    @mock.patch("se_api.services.connector.Connector._get_file_to_index")
    def test__files_to_index_subdata(self, mock_get_file_to_index):
        mock_get_file_to_index.return_value = {"subdata": "subdata"}
        result = self.instance._files_to_index()
        assert result is None
        assert self.instance.subdata == "subdata"

    @mock.patch("se_api.services.connector.Connector._get_file_to_index")
    def test__files_to_index_full(self, mock_get_file_to_index):
        mock_get_file_to_index.return_value = {"file_url": "file_url", "subdata": "subdata"}
        result = self.instance._files_to_index()
        assert result == "file_url"
        assert self.instance.subdata == "subdata"
