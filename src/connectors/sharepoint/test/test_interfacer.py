"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from unittest import IsolatedAsyncioTestCase, mock

from interfacer_sharepoint import SharePoint


class TestSharePoint(IsolatedAsyncioTestCase):
    """Unit tests for the SharePoint interfacer."""

    def setUp(self):
        with mock.patch("interfacer_sharepoint.SharePoint.__init__", return_value=None):
            self.instance = SharePoint()
        self.instance.source_system = "SharePoint"
        self.instance.file_extensions = [".pdf", ".docx", ".txt", ".md"]
        self.instance.extension_descriptions = {
            ".pdf": "PDF",
            ".docx": "Word",
            ".txt": "Text",
            ".md": "Text",
        }

    # --- subdata encoding/decoding ---

    def test_encode_decode_subdata_roundtrip(self):
        delta_map = {"drive_abc": "https://graph.microsoft.com/v1.0/drives/drive_abc/root/delta?token=xyz"}
        encoded = SharePoint._encode_subdata(delta_map)
        decoded = self.instance._decode_subdata(encoded)
        assert decoded == delta_map

    def test_decode_subdata_none_returns_empty(self):
        assert self.instance._decode_subdata(None) == {}

    def test_decode_subdata_invalid_base64_returns_empty(self):
        assert self.instance._decode_subdata("!!!not-valid!!!") == {}

    def test_decode_subdata_valid_base64_non_json_returns_empty(self):
        import base64

        assert self.instance._decode_subdata(base64.urlsafe_b64encode(b"not json").decode()) == {}

    # --- file record building ---

    def test_build_file_record_pdf(self):
        item = {
            "id": "item123",
            "name": "report.pdf",
            "size": 2048,
            "webUrl": "https://tenant.sharepoint.com/report.pdf",
            "lastModifiedDateTime": "2026-01-01T00:00:00Z",
        }
        record = self.instance._build_file_record(item, "drive456")
        assert record is not None
        assert record["metadata"]["file_type"] == ".pdf"
        assert record["metadata"]["file_type_description"] == "PDF"
        assert record["metadata"]["name"] == "report.pdf"
        assert record["metadata"]["size"] == 2048
        assert record["metadata"]["unique_pointer"] == ("https://graph.microsoft.com/v1.0/drives/drive456/items/item123")
        assert record["metadata"]["clickable_url"] == "https://tenant.sharepoint.com/report.pdf"
        assert record["metadata"]["last_edit_date"] == "2026-01-01T00:00:00Z"
        assert record["content"] is None

    def test_build_file_record_unknown_extension_returns_none(self):
        item = {"id": "item123", "name": "script.py", "size": 500}
        assert self.instance._build_file_record(item, "drive456") is None

    def test_build_file_record_folder_returns_none(self):
        item = {"id": "folder1", "name": "Documents", "size": 0, "folder": {"childCount": 3}}
        assert self.instance._build_file_record(item, "drive456") is None

    def test_build_file_record_deleted_tombstone_returns_none(self):
        item = {"id": "item123", "name": "old.pdf", "deleted": {}}
        assert self.instance._build_file_record(item, "drive456") is None

    def test_build_file_record_markdown(self):
        item = {"id": "itemMd", "name": "notes.md", "size": 100, "webUrl": "https://sp.com/notes.md"}
        record = self.instance._build_file_record(item, "drive1")
        assert record is not None
        assert record["metadata"]["file_type"] == ".md"

    # --- check_index_needed ---

    async def test_check_index_needed_no_subdata(self):
        result = await self.instance.check_index_needed(None)
        assert result == {"index_needed": True}

    async def test_check_index_needed_no_changes(self):
        delta_map = {"drive_abc": "https://graph.microsoft.com/v1.0/drives/drive_abc/root/delta?token=xyz"}
        subdata = SharePoint._encode_subdata(delta_map)

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": []}

        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.get.return_value = mock_response

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            result = await self.instance.check_index_needed(subdata)

        assert result == {"index_needed": False}

    async def test_check_index_needed_with_changes(self):
        delta_map = {"drive_abc": "https://graph.microsoft.com/v1.0/drives/drive_abc/root/delta?token=xyz"}
        subdata = SharePoint._encode_subdata(delta_map)

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"id": "changed_item", "name": "changed.pdf"}]}

        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.get.return_value = mock_response

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            result = await self.instance.check_index_needed(subdata)

        assert result == {"index_needed": True}
