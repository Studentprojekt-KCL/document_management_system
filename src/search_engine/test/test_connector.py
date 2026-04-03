from unittest import TestCase, mock
from se_api.services.connector import Connector


class TestConnector(TestCase):
    @mock.patch("se_api.services.connector.Connector.__init__", return_value=None)
    def setUp(self, _):
        self.instance = Connector()
        self.instance.address = ""
        self.instance.url_files = "/files"
        self.instance.url_file = "/file"
        self.instance.url_files_to_index = "/files_to_index"
        self.instance.subdata = None

    def test_reset(self):
        self.instance.subdata = ""
        self.instance.reset()
        assert self.instance.subdata is None

    # ==== GET_FILE_POINTERS ====

    @mock.patch("se_api.services.connector.Connector._get_file_pointers")
    def test_get_file_pointers_dict(self, mock_get_file_pointers):
        mock_get_file_pointers.return_value = {}
        result = self.instance.get_file_pointers()
        assert result == []

    @mock.patch("se_api.services.connector.Connector._get_file_pointers")
    def test_get_file_pointers_empty(self, mock_get_file_pointers):
        mock_get_file_pointers.return_value = []
        result = self.instance.get_file_pointers()
        assert result == []

    @mock.patch("se_api.services.connector.Connector._get_file_pointers")
    def test_get_file_pointers_none(self, mock_get_file_pointers):
        mock_get_file_pointers.return_value = None
        result = self.instance.get_file_pointers()
        assert result == []

    @mock.patch("se_api.services.connector.Connector._get_file_pointers")
    def test_get_file_pointers_valid(self, mock_get_file_pointers):
        mock_get_file_pointers.return_value = {"file_pointers": ["pointer-1", "pointer-2", "pointer-3"]}
        result = self.instance.get_file_pointers()
        assert result == ["pointer-1", "pointer-2", "pointer-3"]

    # ==== GET_FILE_FROM_POINTER ====

    @mock.patch("se_api.services.connector.Connector._get_file_from_pointer")
    def test_get_file_dict(self, mock_get_file_from_pointer):
        mock_get_file_from_pointer.return_value = {}
        result = self.instance.get_file("")
        assert result == {}

    @mock.patch("se_api.services.connector.Connector._get_file_from_pointer")
    def test_get_file_list(self, mock_get_file_from_pointer):
        mock_get_file_from_pointer.return_value = []
        result = self.instance.get_file("")
        assert result is None

    @mock.patch("se_api.services.connector.Connector._get_file_from_pointer")
    def test_get_file_empty(self, mock_get_file_from_pointer):
        mock_get_file_from_pointer.return_value = None
        result = self.instance.get_file("")
        assert result is None

    @mock.patch("se_api.services.connector.Connector._get_file_from_pointer")
    def test_get_file_full(self, mock_get_file_from_pointer):
        mock_get_file_from_pointer.return_value = {"content": "content", "metadata": {"item1": "item", "item2": "item"}}
        result = self.instance.get_file("")
        assert result == {"content": "content", "metadata": {"item1": "item", "item2": "item"}}

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
