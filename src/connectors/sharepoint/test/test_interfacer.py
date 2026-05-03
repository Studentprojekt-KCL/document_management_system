"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import asyncio
import base64
import json
from unittest import IsolatedAsyncioTestCase, mock

import httpx

from interfacer_sharepoint import DEFAULT_GRAPH_BASE, MAX_RETRIES, SharePoint, _HttpCtx

GRAPH_BASE = DEFAULT_GRAPH_BASE

# _HttpCtx used in tests that call private methods directly.
# Semaphore limit is effectively unlimited so tests never block.
_CTX = _HttpCtx(client=None, sem=asyncio.Semaphore(100), token="token")


def _mock_response(status_code, data=None):
    response = mock.MagicMock()
    response.status_code = status_code
    response.headers = {}
    if data is not None:
        response.json.return_value = data
    return response


def _mock_client_ctx(*responses):
    """Context-manager mock of httpx.AsyncClient for public methods that own the client."""
    client = mock.AsyncMock()
    client.__aenter__ = mock.AsyncMock(return_value=client)
    client.__aexit__ = mock.AsyncMock(return_value=None)
    if len(responses) == 1:
        client.get.return_value = responses[0]
    else:
        client.get.side_effect = list(responses)
    return client


def _mock_client(*responses):
    """Plain mock httpx.AsyncClient for methods that receive ctx as a parameter."""
    client = mock.AsyncMock(spec=httpx.AsyncClient)
    if len(responses) == 1:
        client.get.return_value = responses[0]
    else:
        client.get.side_effect = list(responses)
    return client


def _ctx(*responses):
    """Build an _HttpCtx with a mock client loaded with the given responses."""
    return _HttpCtx(client=_mock_client(*responses), sem=asyncio.Semaphore(100), token="token")


class TestSharePoint(IsolatedAsyncioTestCase):
    """Unit tests for the SharePoint interfacer."""

    def setUp(self):
        with mock.patch("interfacer_sharepoint.SharePoint.__init__", return_value=None):
            self.instance = SharePoint()
        self.instance.graph_base = GRAPH_BASE
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
        delta_map = {"drive_abc": "xyz"}
        encoded = SharePoint._encode_subdata(delta_map)
        decoded = self.instance._decode_subdata(encoded)
        assert decoded == delta_map

    def test_decode_subdata_none_returns_empty(self):
        assert self.instance._decode_subdata(None) == {}

    def test_decode_subdata_invalid_base64_returns_empty(self):
        assert self.instance._decode_subdata("!!!not-valid!!!") == {}

    def test_decode_subdata_valid_base64_non_json_returns_empty(self):
        assert self.instance._decode_subdata(base64.urlsafe_b64encode(b"not json").decode()) == {}

    def test_init_graph_base_defaults_when_env_unset(self):
        def fake_read_env(name, required=True):
            if name == "CONSHAREPOINT_GRAPH_BASE":
                return None
            if name == "CONSHAREPOINT_SYSTEM_NAME":
                return "SharePoint"
            return ""

        with mock.patch("interfacer_sharepoint.read_env_variable", side_effect=fake_read_env):
            with mock.patch(
                "interfacer_sharepoint.get_file_resource",
                return_value=[{"extension": ".pdf", "description": "PDF"}],
            ):
                inst = SharePoint()
        assert inst.graph_base == DEFAULT_GRAPH_BASE

    def test_init_graph_base_from_env_strips_whitespace_and_slash(self):
        def fake_read_env(name, required=True):
            if name == "CONSHAREPOINT_GRAPH_BASE":
                return " https://graph.microsoft.com/beta/ "
            if name == "CONSHAREPOINT_SYSTEM_NAME":
                return "SharePoint"
            return ""

        with mock.patch("interfacer_sharepoint.read_env_variable", side_effect=fake_read_env):
            with mock.patch(
                "interfacer_sharepoint.get_file_resource",
                return_value=[{"extension": ".pdf", "description": "PDF"}],
            ):
                inst = SharePoint()
        assert inst.graph_base == "https://graph.microsoft.com/beta"

    def test_init_graph_base_blank_env_uses_default(self):
        def fake_read_env(name, required=True):
            if name == "CONSHAREPOINT_GRAPH_BASE":
                return "  \t  "
            if name == "CONSHAREPOINT_SYSTEM_NAME":
                return "SharePoint"
            return ""

        with mock.patch("interfacer_sharepoint.read_env_variable", side_effect=fake_read_env):
            with mock.patch(
                "interfacer_sharepoint.get_file_resource",
                return_value=[{"extension": ".pdf", "description": "PDF"}],
            ):
                inst = SharePoint()
        assert inst.graph_base == DEFAULT_GRAPH_BASE

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
        assert "content" not in record

    def test_build_file_record_unknown_extension_returns_record(self):
        item = {"id": "item123", "name": "script.py", "size": 500}
        record = self.instance._build_file_record(item, "drive456")
        assert record is not None
        assert record["metadata"]["file_type"] == "Unknown"

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

    # --- _get_with_retry ---

    async def test_get_with_retry_succeeds_on_first_attempt(self):
        resp = _mock_response(200, {"value": []})
        ctx = _ctx(resp)
        result = await self.instance._get_with_retry(ctx, "https://example.com")
        assert result.status_code == 200
        assert ctx.client.get.call_count == 1

    async def test_get_with_retry_retries_on_429(self):
        rate_limited = _mock_response(429)
        rate_limited.headers = {"Retry-After": "1"}
        success = _mock_response(200, {"value": []})
        ctx = _ctx(rate_limited, success)
        with mock.patch("asyncio.sleep") as mock_sleep:
            result = await self.instance._get_with_retry(ctx, "https://example.com")
        assert result.status_code == 200
        assert ctx.client.get.call_count == 2
        mock_sleep.assert_called_once_with(1)

    async def test_get_with_retry_exhausts_retries(self):
        rate_limited = _mock_response(429)
        rate_limited.headers = {"Retry-After": "1"}
        ctx = _ctx(*[rate_limited] * MAX_RETRIES)
        with mock.patch("asyncio.sleep"):
            result = await self.instance._get_with_retry(ctx, "https://example.com")
        assert result.status_code == 429
        assert ctx.client.get.call_count == MAX_RETRIES

    # --- _get_sites ---

    async def test_get_sites_success(self):
        ctx = _ctx(_mock_response(200, {"value": [{"id": "site1"}, {"id": "site2"}]}))
        sites = await self.instance._get_sites(ctx)
        assert [s["id"] for s in sites] == ["site1", "site2"]

    async def test_get_sites_pagination(self):
        page1 = _mock_response(
            200,
            {
                "value": [{"id": "site1"}],
                "@odata.nextLink": f"{GRAPH_BASE}/sites?$skiptoken=page2",
            },
        )
        page2 = _mock_response(200, {"value": [{"id": "site2"}]})
        ctx = _ctx(page1, page2)
        sites = await self.instance._get_sites(ctx)
        assert [s["id"] for s in sites] == ["site1", "site2"]

    async def test_get_sites_non_200_returns_empty(self):
        ctx = _ctx(_mock_response(403))
        sites = await self.instance._get_sites(ctx)
        assert sites == []

    # --- _get_drives ---

    async def test_get_drives_success(self):
        ctx = _ctx(_mock_response(200, {"value": [{"id": "drive1"}, {"id": "drive2"}]}))
        drives = await self.instance._get_drives(ctx, "site1")
        assert len(drives) == 2

    async def test_get_drives_non_200_returns_empty(self):
        ctx = _ctx(_mock_response(404))
        drives = await self.instance._get_drives(ctx, "site1")
        assert drives == []

    # --- _run_delta_query ---

    async def test_run_delta_query_single_page(self):
        new_link = f"{GRAPH_BASE}/drives/d1/root/delta?token=new"
        ctx = _ctx(_mock_response(200, {"value": [{"id": "item1"}, {"id": "item2"}], "@odata.deltaLink": new_link}))
        items, delta_link = await self.instance._run_delta_query(ctx, f"{GRAPH_BASE}/drives/d1/root/delta")
        assert len(items) == 2
        assert delta_link == new_link

    async def test_run_delta_query_pagination(self):
        new_link = f"{GRAPH_BASE}/drives/d1/root/delta?token=new"
        page1 = _mock_response(
            200,
            {
                "value": [{"id": "item1"}],
                "@odata.nextLink": f"{GRAPH_BASE}/drives/d1/root/delta?$skiptoken=p2",
            },
        )
        page2 = _mock_response(200, {"value": [{"id": "item2"}], "@odata.deltaLink": new_link})
        ctx = _ctx(page1, page2)
        items, delta_link = await self.instance._run_delta_query(ctx, f"{GRAPH_BASE}/drives/d1/root/delta")
        assert [i["id"] for i in items] == ["item1", "item2"]
        assert delta_link == new_link

    async def test_run_delta_query_non_200_returns_empty(self):
        ctx = _ctx(_mock_response(410))
        items, delta_link = await self.instance._run_delta_query(ctx, f"{GRAPH_BASE}/drives/d1/root/delta")
        assert items == []
        assert delta_link == ""

    # --- _process_drive ---

    async def test_process_drive_encodes_content_when_fetch_ok(self):
        new_link = f"{GRAPH_BASE}/drives/drive456/root/delta?token=new"
        item = {
            "id": "item123",
            "name": "report.pdf",
            "size": 2048,
            "webUrl": "https://sp.com/report.pdf",
            "lastModifiedDateTime": "2026-01-01T00:00:00Z",
        }
        self.instance._run_delta_query = mock.AsyncMock(return_value=([item], new_link))
        content_resp = _mock_response(200)
        content_resp.content = b"bytes-from-graph"
        ctx = _ctx(content_resp)
        drive_id, records, delta_link = await self.instance._process_drive(
            ctx, "drive456", f"{GRAPH_BASE}/drives/drive456/root/delta"
        )
        assert drive_id == "drive456"
        assert delta_link == new_link
        assert len(records) == 1
        assert records[0]["content"] == base64.b64encode(b"bytes-from-graph").decode("utf-8")
        assert records[0]["metadata"]["name"] == "report.pdf"
        assert ctx.client.get.call_count == 1

    async def test_process_drive_content_forbidden_yields_empty_base64(self):
        new_link = f"{GRAPH_BASE}/drives/drive456/root/delta?token=new"
        item = {
            "id": "item123",
            "name": "notes.txt",
            "size": 10,
            "webUrl": "https://sp.com/notes.txt",
        }
        self.instance._run_delta_query = mock.AsyncMock(return_value=([item], new_link))
        ctx = _ctx(_mock_response(403))
        _, records, _ = await self.instance._process_drive(ctx, "drive456", f"{GRAPH_BASE}/drives/drive456/root/delta")
        assert len(records) == 1
        assert records[0]["content"] == ""
        assert records[0]["metadata"]["file_type"] == ".txt"

    # --- _collect_drive_tasks ---

    async def test_collect_drive_tasks_with_sites(self):
        self.instance._get_sites = mock.AsyncMock(return_value=[{"id": "site1"}])
        self.instance._get_drives = mock.AsyncMock(return_value=[{"id": "drive1"}])
        tasks = await self.instance._collect_drive_tasks(_CTX, {})
        assert tasks == [("drive1", f"{GRAPH_BASE}/drives/drive1/root/delta")]

    async def test_collect_drive_tasks_uses_stored_delta_link(self):
        self.instance._get_sites = mock.AsyncMock(return_value=[{"id": "site1"}])
        self.instance._get_drives = mock.AsyncMock(return_value=[{"id": "drive1"}])
        tasks = await self.instance._collect_drive_tasks(_CTX, {"drive1": "stored"})
        assert tasks == [("drive1", f"{GRAPH_BASE}/drives/drive1/root/delta?token=stored")]

    async def test_collect_drive_tasks_multiple_sites(self):
        self.instance._get_sites = mock.AsyncMock(return_value=[{"id": "site1"}, {"id": "site2"}])
        self.instance._get_drives = mock.AsyncMock(return_value=[{"id": "driveA"}])
        tasks = await self.instance._collect_drive_tasks(_CTX, {})
        assert len(tasks) == 2
        assert all(drive_id == "driveA" for drive_id, _ in tasks)

    async def test_collect_drive_tasks_no_sites_returns_empty(self):
        self.instance._get_sites = mock.AsyncMock(return_value=[])
        tasks = await self.instance._collect_drive_tasks(_CTX, {})
        assert tasks == []

    async def test_collect_drive_tasks_skips_empty_site_id(self):
        self.instance._get_sites = mock.AsyncMock(return_value=[{"id": ""}, {"id": "site1"}])
        self.instance._get_drives = mock.AsyncMock(return_value=[{"id": "drive1"}])
        tasks = await self.instance._collect_drive_tasks(_CTX, {})
        assert len(tasks) == 1
        assert tasks[0][0] == "drive1"

    async def test_collect_drive_tasks_site_exception_is_skipped(self):
        self.instance._get_sites = mock.AsyncMock(return_value=[{"id": "site1"}, {"id": "site2"}])
        self.instance._get_drives = mock.AsyncMock(side_effect=[ConnectionError("timeout"), [{"id": "drive2"}]])
        tasks = await self.instance._collect_drive_tasks(_CTX, {})
        assert len(tasks) == 1
        assert tasks[0][0] == "drive2"

    # --- _get_file ---

    async def test_get_file_metadata_only(self):
        ctx = _ctx(
            _mock_response(
                200,
                {
                    "name": "report.pdf",
                    "size": 1024,
                    "webUrl": "https://tenant.sharepoint.com/report.pdf",
                    "lastModifiedDateTime": "2026-01-01T00:00:00Z",
                },
            )
        )
        result = await self.instance._get_file(ctx, f"{GRAPH_BASE}/drives/d1/items/i1")
        assert result["name"] == "report.pdf"
        assert result["file_type"] == ".pdf"
        assert result["last_edit_date"] == "2026-01-01T00:00:00Z"
        assert "content" not in result

    async def test_get_file_non_200_returns_empty(self):
        ctx = _ctx(_mock_response(404))
        result = await self.instance._get_file(ctx, f"{GRAPH_BASE}/drives/d1/items/i1")
        assert result == {}

    async def test_get_file_unknown_extension_returns_empty(self):
        ctx = _ctx(_mock_response(200, {"name": "script.py", "size": 100, "webUrl": "https://sp.com/script.py"}))
        result = await self.instance._get_file(ctx, f"{GRAPH_BASE}/drives/d1/items/i1")
        assert result == {}

    async def test_get_file_exclude_last_edit_date(self):
        ctx = _ctx(_mock_response(200, {"name": "report.pdf", "size": 512, "webUrl": "https://sp.com/report.pdf"}))
        result = await self.instance._get_file(ctx, f"{GRAPH_BASE}/drives/d1/items/i1", include_last_edit_date=False)
        assert "last_edit_date" not in result

    async def test_get_file_with_content(self):
        meta_resp = _mock_response(200, {"name": "doc.docx", "size": 512, "webUrl": "https://sp.com/doc.docx"})
        content_resp = _mock_response(200)
        content_resp.content = b"file bytes"
        ctx = _ctx(meta_resp, content_resp)
        result = await self.instance._get_file(ctx, f"{GRAPH_BASE}/drives/d1/items/i1", include_content=True)
        assert result["content"] == base64.b64encode(b"file bytes").decode("utf-8")

    # --- _fetch_record_content ---

    async def test_fetch_record_content_success(self):
        content_resp = _mock_response(200)
        content_resp.content = b"file bytes"
        ctx = _ctx(content_resp)
        record = {"content": None, "metadata": {"unique_pointer": f"{GRAPH_BASE}/drives/d1/items/i1", "name": "doc.pdf"}}
        await self.instance._fetch_record_content(ctx, record)
        assert record["content"] == base64.b64encode(b"file bytes").decode("utf-8")

    async def test_fetch_record_content_non_200_leaves_content_none(self):
        ctx = _ctx(_mock_response(403))
        record = {"content": None, "metadata": {"unique_pointer": f"{GRAPH_BASE}/drives/d1/items/i1", "name": "doc.pdf"}}
        await self.instance._fetch_record_content(ctx, record)
        assert record["content"] is None

    # --- stream_files_to_index ---

    async def test_stream_files_to_index_yields_subdata_then_records(self):
        new_link = f"{GRAPH_BASE}/drives/drive1/root/delta?token=new"
        item = {
            "id": "item1",
            "name": "report.pdf",
            "size": 2048,
            "webUrl": "https://sp.com/report.pdf",
            "lastModifiedDateTime": "2026-01-01T00:00:00Z",
        }
        self.instance._collect_drive_tasks = mock.AsyncMock(return_value=[("drive1", f"{GRAPH_BASE}/drives/drive1/root/delta")])
        self.instance._run_delta_query = mock.AsyncMock(return_value=([item], new_link))

        async def _set_content(_, record):
            record["content"] = base64.b64encode(b"bytes").decode("utf-8")

        self.instance._fetch_record_content = mock.AsyncMock(side_effect=_set_content)
        chunks = []
        async for chunk in self.instance.stream_files_to_index(None, "token"):
            chunks.append(json.loads(chunk))
        assert "subdata" in chunks[0]
        assert len(chunks) == 2
        assert chunks[1]["metadata"]["name"] == "report.pdf"
        assert chunks[1]["content"] == base64.b64encode(b"bytes").decode("utf-8")

    async def test_stream_files_to_index_drive_exception_is_skipped(self):
        self.instance._collect_drive_tasks = mock.AsyncMock(return_value=[("drive1", f"{GRAPH_BASE}/drives/drive1/root/delta")])
        self.instance._run_delta_query = mock.AsyncMock(side_effect=ConnectionError("network failure"))
        self.instance._fetch_record_content = mock.AsyncMock()
        chunks = []
        async for chunk in self.instance.stream_files_to_index(None, "token"):
            chunks.append(json.loads(chunk))
        assert len(chunks) == 1
        assert "subdata" in chunks[0]
        assert chunks[0]["subdata"] == SharePoint._encode_subdata({})

    async def test_stream_files_to_index_no_drives_yields_only_subdata(self):
        self.instance._collect_drive_tasks = mock.AsyncMock(return_value=[])
        self.instance._fetch_record_content = mock.AsyncMock()
        chunks = []
        async for chunk in self.instance.stream_files_to_index(None, "token"):
            chunks.append(json.loads(chunk))
        assert len(chunks) == 1
        assert "subdata" in chunks[0]

    async def test_stream_files_to_index_passes_all_file_types(self):
        new_link = f"{GRAPH_BASE}/drives/drive1/root/delta?token=new"
        items = [
            {"id": "i1", "name": "report.pdf", "size": 100, "webUrl": "https://sp.com/report.pdf"},
            {"id": "i2", "name": "script.py", "size": 200, "webUrl": "https://sp.com/script.py"},
        ]
        self.instance._collect_drive_tasks = mock.AsyncMock(return_value=[("drive1", f"{GRAPH_BASE}/drives/drive1/root/delta")])
        self.instance._run_delta_query = mock.AsyncMock(return_value=(items, new_link))
        self.instance._fetch_record_content = mock.AsyncMock()
        chunks = []
        async for chunk in self.instance.stream_files_to_index(None, "token"):
            chunks.append(json.loads(chunk))
        assert len(chunks) == 3
        names = {c["metadata"]["name"] for c in chunks[1:]}
        assert names == {"report.pdf", "script.py"}

    # --- check_index_needed ---

    async def test_check_index_needed_no_subdata(self):
        result = await self.instance.check_index_needed(None)
        assert result == {"index_needed": True}

    async def test_check_index_needed_parallel_no_changes(self):
        delta_map = {"drive_a": "a", "drive_b": "b"}
        subdata = SharePoint._encode_subdata(delta_map)
        empty = _mock_response(200, {"value": []})
        with mock.patch("httpx.AsyncClient", return_value=_mock_client_ctx(empty, empty)):
            result = await self.instance.check_index_needed(subdata)
        assert result == {"index_needed": False}

    async def test_check_index_needed_parallel_one_drive_changed(self):
        delta_map = {"drive_abc": "xyz"}
        subdata = SharePoint._encode_subdata(delta_map)
        with mock.patch(
            "httpx.AsyncClient",
            return_value=_mock_client_ctx(_mock_response(200, {"value": [{"id": "changed_item"}]})),
        ):
            result = await self.instance.check_index_needed(subdata)
        assert result == {"index_needed": True}

    async def test_check_index_needed_expired_token_returns_index_needed(self):
        delta_map = {"drive_abc": "xyz"}
        subdata = SharePoint._encode_subdata(delta_map)
        with mock.patch("httpx.AsyncClient", return_value=_mock_client_ctx(_mock_response(410))):
            result = await self.instance.check_index_needed(subdata)
        assert result == {"index_needed": True}

    async def test_check_index_needed_parallel_drive_exception(self):
        delta_map = {"drive_abc": "xyz"}
        subdata = SharePoint._encode_subdata(delta_map)
        self.instance._check_drive_delta = mock.AsyncMock(side_effect=ConnectionError("timeout"))
        result = await self.instance.check_index_needed(subdata)
        assert result == {"index_needed": True}
