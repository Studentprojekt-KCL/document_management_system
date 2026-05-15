"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

Contract tests for the SharePoint interfacer.
"""

# Tests intentionally exercise private helpers so failures point at a precise
# connector responsibility instead of a broad end-to-end symptom.
# pylint: disable=protected-access

import asyncio
import base64
import gzip
import json
from unittest import IsolatedAsyncioTestCase, TestCase, mock
from urllib.parse import parse_qs, urlparse

import httpx

from interfacer_sharepoint import MAX_RETRIES, SharePoint, _HttpCtx

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
TOKEN = "access-token"


def graph_url(path: str) -> str:
    """Return a Microsoft Graph URL for a slash-prefixed path."""
    return f"{GRAPH_BASE}{path}"


def response(status_code: int = 200, payload: dict | None = None, content: bytes = b"") -> mock.MagicMock:
    """Build the small httpx.Response surface used by the SharePoint connector."""
    res = mock.MagicMock(spec=httpx.Response)
    res.status_code = status_code
    res.headers = {}
    res.content = content
    res.json.return_value = payload if payload is not None else {}
    return res


def http_context(client: mock.AsyncMock | None = None) -> _HttpCtx:
    """Create a request context with a permissive semaphore for unit tests."""
    return _HttpCtx(client or mock.AsyncMock(spec=httpx.AsyncClient), asyncio.Semaphore(100), TOKEN)


def async_client_context(client: mock.AsyncMock) -> mock.MagicMock:
    """Wrap a mocked AsyncClient in the async context manager API."""
    manager = mock.MagicMock()
    manager.__aenter__ = mock.AsyncMock(return_value=client)
    manager.__aexit__ = mock.AsyncMock(return_value=None)
    return manager


class SharePointTestCase(TestCase):
    """Base class that constructs SharePoint without reading process environment."""

    def setUp(self) -> None:
        with mock.patch.object(SharePoint, "__init__", return_value=None):
            self.sharepoint = SharePoint()
        self.sharepoint.graph_base = GRAPH_BASE
        self.sharepoint.source_system = "SharePoint"
        self.sharepoint.file_extensions = [".pdf", ".docx", ".txt", ".md"]
        self.sharepoint.extension_descriptions = {
            ".pdf": "PDF",
            ".docx": "Word document",
            ".txt": "Text document",
            ".md": "Markdown document",
        }


class TestSharePointConfiguration(TestCase):
    """Constructor and subdata serialization behavior."""

    def test_init_normalizes_graph_base_and_loads_file_type_metadata(self) -> None:
        """Graph base URLs should be usable even when env values include whitespace or a trailing slash."""

        def fake_read_env(name: str, *_args, **_kwargs) -> str:
            return {
                "CONSHAREPOINT_GRAPH_BASE": " https://graph.microsoft.com/beta/ ",
                "CONSHAREPOINT_SYSTEM_NAME": "Company SharePoint",
            }[name]

        file_types = [{"extension": ".pdf", "description": "PDF document"}]
        with mock.patch("interfacer_sharepoint.read_env_variable", side_effect=fake_read_env), mock.patch(
            "interfacer_sharepoint.get_file_resource", return_value=file_types
        ):
            sharepoint = SharePoint()

        self.assertEqual(sharepoint.graph_base, "https://graph.microsoft.com/beta")
        self.assertEqual(sharepoint.source_system, "Company SharePoint")
        self.assertEqual(sharepoint.file_extensions, [".pdf"])
        self.assertEqual(sharepoint.extension_descriptions, {".pdf": "PDF document"})

    def test_subdata_round_trips_delta_tokens_as_gzip_base64_json(self) -> None:
        """The indexer can persist and pass back a compact per-drive delta-token map."""
        delta_map = {"drive-a": "token-a", "drive-b": "token-b"}

        encoded = SharePoint._encode_subdata(delta_map)

        self.assertEqual(SharePoint._decode_subdata(encoded), delta_map)
        raw_json = gzip.decompress(base64.urlsafe_b64decode(encoded)).decode("utf-8")
        self.assertEqual(json.loads(raw_json), delta_map)

    def test_decode_subdata_treats_missing_or_invalid_values_as_a_fresh_sync(self) -> None:
        """Bad caller state must not crash sync decisions or streaming."""
        self.assertEqual(SharePoint._decode_subdata(None), {})
        self.assertEqual(SharePoint._decode_subdata("not-valid-base64"), {})
        self.assertEqual(SharePoint._decode_subdata(base64.urlsafe_b64encode(b"not gzip").decode("utf-8")), {})


class TestSharePointRecordBuilding(SharePointTestCase):
    """Mapping Microsoft Graph drive items to DMIS file records."""

    def test_build_file_record_maps_graph_item_to_index_metadata(self) -> None:
        """A driveItem file becomes a metadata-only record that later receives content."""
        item = {
            "id": "item-123",
            "name": "Quarterly Report.pdf",
            "size": 2048,
            "webUrl": "https://tenant.sharepoint.com/sites/team/Quarterly%20Report.pdf",
            "lastModifiedDateTime": "2026-05-01T10:20:30Z",
        }

        record = self.sharepoint._build_file_record(item, "drive-456")

        self.assertIsNotNone(record)
        self.assertEqual(
            record,
            {
                    "unique_pointer": graph_url("/drives/drive-456/items/item-123"),
                    "name": "Quarterly Report.pdf",
                    "size": 2048,
                    "type": "source_file",
                    "source_system": "SharePoint",
                    "last_edit_date": "2026-05-01T10:20:30Z",
                    "clickable_url": "https://tenant.sharepoint.com/sites/team/Quarterly%20Report.pdf",
                    "file_type": ".pdf",
                    "file_type_description": "PDF",
            },
        )

    def test_build_file_record_keeps_unknown_extensions_indexable(self) -> None:
        """Unknown extensions are still useful search records, just labelled as Unknown."""
        record = self.sharepoint._build_file_record({"id": "item-1", "name": "build.lock", "size": 12}, "drive-1")

        self.assertIsNotNone(record)
        self.assertEqual(record["file_type"], "Unknown")
        self.assertEqual(record["file_type_description"], "Unknown")

    def test_build_file_record_ignores_non_file_delta_items(self) -> None:
        """Folder entries and delete tombstones are not documents to index."""
        folder = {"id": "folder-1", "name": "Documents", "folder": {"childCount": 4}}
        deleted_file = {"id": "file-1", "name": "old.pdf", "deleted": {}}

        self.assertIsNone(self.sharepoint._build_file_record(folder, "drive-1"))
        self.assertIsNone(self.sharepoint._build_file_record(deleted_file, "drive-1"))


class TestSharePointHttp(IsolatedAsyncioTestCase):
    """HTTP retry and request composition behavior."""

    async def test_request_with_retry_adds_bearer_token_and_returns_success(self) -> None:
        """All Graph requests should carry the per-user OAuth token."""
        client = mock.AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = response(200, {"value": []})

        result = await SharePoint._request_with_retry(http_context(client), "https://example.test/files")

        self.assertEqual(result.status_code, httpx.codes.OK)
        client.get.assert_awaited_once_with(
            "https://example.test/files",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    async def test_request_with_retry_uses_caller_supplied_headers_without_overwriting_them(self) -> None:
        """Callers can pass special Graph headers when an endpoint requires them."""
        client = mock.AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = response(200, {"value": []})

        await SharePoint._request_with_retry(http_context(client), "https://example.test/files", headers={"Prefer": "delta"})

        client.get.assert_awaited_once_with("https://example.test/files", headers={"Prefer": "delta"})

    async def test_request_with_retry_respects_retry_after_for_429(self) -> None:
        """429 responses should be retried according to Retry-After before giving up."""
        rate_limited = response(429)
        rate_limited.headers = {"Retry-After": "2"}
        client = mock.AsyncMock(spec=httpx.AsyncClient)
        client.get.side_effect = [rate_limited, response(200, {"ok": True})]

        with mock.patch("interfacer_sharepoint.asyncio.sleep", new=mock.AsyncMock()) as sleep:
            result = await SharePoint._request_with_retry(http_context(client), "https://example.test/files")

        self.assertEqual(result.status_code, httpx.codes.OK)
        self.assertEqual(client.get.await_count, 2)
        sleep.assert_awaited_once_with(2)

    async def test_request_with_retry_returns_final_429_after_retry_budget_is_exhausted(self) -> None:
        """The caller, not the retry helper, decides how to handle persistent throttling."""
        client = mock.AsyncMock(spec=httpx.AsyncClient)
        client.get.side_effect = [response(429) for _ in range(MAX_RETRIES)]

        with mock.patch("interfacer_sharepoint.asyncio.sleep", new=mock.AsyncMock()):
            result = await SharePoint._request_with_retry(http_context(client), "https://example.test/files")

        self.assertEqual(result.status_code, httpx.codes.TOO_MANY_REQUESTS)
        self.assertEqual(client.get.await_count, MAX_RETRIES)


class TestSharePointGraphDiscovery(SharePointTestCase, IsolatedAsyncioTestCase):
    """Microsoft Graph discovery and delta query behavior."""

    async def test_get_sites_uses_microsoft_search_and_paginates(self) -> None:
        """Accessible SharePoint sites come from POST /search/query across all pages."""
        first_page = response(
            200,
            {"value": [{"hitsContainers": [{"hits": [{"resource": {"id": "site-a"}}], "moreResultsAvailable": True}]}]},
        )
        second_page = response(
            200,
            {
                "value": [
                    {
                        "hitsContainers": [
                            {"hits": [{"resource": {"id": "site-b"}}, {"resource": {}}], "moreResultsAvailable": False}
                        ]
                    }
                ]
            },
        )
        self.sharepoint._request_with_retry = mock.AsyncMock(side_effect=[first_page, second_page])

        sites = await self.sharepoint._get_sites(http_context())

        self.assertEqual(sites, [{"id": "site-a"}, {"id": "site-b"}])
        self.assertEqual(self.sharepoint._request_with_retry.await_count, 2)
        first_call = self.sharepoint._request_with_retry.await_args_list[0]
        second_call = self.sharepoint._request_with_retry.await_args_list[1]
        self.assertEqual(first_call.args[1], graph_url("/search/query"))
        self.assertEqual(first_call.kwargs["method"], "post")
        self.assertEqual(first_call.kwargs["json"]["requests"][0]["from"], 0)
        self.assertEqual(second_call.kwargs["json"]["requests"][0]["from"], 500)

    async def test_get_sites_returns_collected_sites_when_a_later_page_fails(self) -> None:
        """A transient later-page failure should not discard already discovered sites."""
        page = response(
            200,
            {"value": [{"hitsContainers": [{"hits": [{"resource": {"id": "site-a"}}], "moreResultsAvailable": True}]}]},
        )
        self.sharepoint._request_with_retry = mock.AsyncMock(side_effect=[page, response(503)])

        self.assertEqual(await self.sharepoint._get_sites(http_context()), [{"id": "site-a"}])

    async def test_get_drives_returns_libraries_and_treats_forbidden_or_missing_sites_as_skippable(self) -> None:
        """403/404 means this site has no listable drives for this user, not that the whole sync failed."""
        self.sharepoint._request_with_retry = mock.AsyncMock(return_value=response(200, {"value": [{"id": "drive-a"}]}))
        self.assertEqual(await self.sharepoint._get_drives(http_context(), "site-a"), [{"id": "drive-a"}])

        self.sharepoint._request_with_retry = mock.AsyncMock(return_value=response(403))
        self.assertEqual(await self.sharepoint._get_drives(http_context(), "site-b"), [])

        self.sharepoint._request_with_retry = mock.AsyncMock(return_value=response(404))
        self.assertEqual(await self.sharepoint._get_drives(http_context(), "site-c"), [])

    async def test_run_delta_query_accumulates_pages_until_delta_link(self) -> None:
        """Delta queries may return nextLink pages before the final reusable deltaLink."""
        final_delta = graph_url("/drives/drive-a/root/delta?token=new-token")
        self.sharepoint._request_with_retry = mock.AsyncMock(
            side_effect=[
                response(
                    200,
                    {
                        "value": [{"id": "item-a"}],
                        "@odata.nextLink": graph_url("/drives/drive-a/root/delta?$skiptoken=next"),
                    },
                ),
                response(200, {"value": [{"id": "item-b"}], "@odata.deltaLink": final_delta}),
            ]
        )

        items, delta_link = await self.sharepoint._run_delta_query(http_context(), graph_url("/drives/drive-a/root/delta"))

        self.assertEqual(items, [{"id": "item-a"}, {"id": "item-b"}])
        self.assertEqual(delta_link, final_delta)

    async def test_run_delta_query_returns_partial_items_without_delta_link_when_graph_fails(self) -> None:
        """The caller can still decide what to do with partial records when a later page fails."""
        self.sharepoint._request_with_retry = mock.AsyncMock(
            side_effect=[
                response(200, {"value": [{"id": "item-a"}], "@odata.nextLink": "next-page"}),
                response(410),
            ]
        )

        self.assertEqual(await self.sharepoint._run_delta_query(http_context(), "first-page"), ([{"id": "item-a"}], ""))

    async def test_collect_drive_tasks_builds_fresh_and_incremental_delta_urls(self) -> None:
        """Every accessible drive becomes one delta task, using stored tokens when present."""
        self.sharepoint._get_sites = mock.AsyncMock(return_value=[{"id": "site-a"}, {"id": "site-b"}])
        self.sharepoint._get_drives = mock.AsyncMock(
            side_effect=[
                [{"id": "drive-a"}, {"id": "drive-b"}],
                [{"id": "drive-c"}, {"id": ""}],
            ]
        )

        tasks = await self.sharepoint._collect_drive_tasks(http_context(), {"drive-b": "old-token"})

        self.assertEqual(
            tasks,
            [
                ("drive-a", graph_url("/drives/drive-a/root/delta")),
                ("drive-b", graph_url("/drives/drive-b/root/delta?token=old-token")),
                ("drive-c", graph_url("/drives/drive-c/root/delta")),
            ],
        )

    async def test_collect_drive_tasks_skips_malformed_sites_and_failed_drive_lists(self) -> None:
        """A bad site entry or inaccessible site should not block other sites in the same sync."""
        self.sharepoint._get_sites = mock.AsyncMock(return_value=[{}, {"id": ""}, {"id": "site-a"}, {"id": "site-b"}])
        self.sharepoint._get_drives = mock.AsyncMock(side_effect=[ConnectionError("timeout"), [{"id": "drive-b"}]])

        tasks = await self.sharepoint._collect_drive_tasks(http_context(), {})

        self.assertEqual(tasks, [("drive-b", graph_url("/drives/drive-b/root/delta"))])
        self.sharepoint._get_drives.assert_has_awaits(
            [mock.call(mock.ANY, "site-a"), mock.call(mock.ANY, "site-b")],
            any_order=True,
        )


class TestSharePointFileFetching(SharePointTestCase, IsolatedAsyncioTestCase):
    """Direct file retrieval and content download behavior."""

    async def test_get_file_returns_metadata_and_optional_content(self) -> None:
        """get_files consumers can request a stable metadata object plus base64 content."""
        self.sharepoint._request_with_retry = mock.AsyncMock(
            side_effect=[
                response(
                    200,
                    {
                        "name": "Plan.docx",
                        "size": 128,
                        "webUrl": "https://tenant.sharepoint.com/Plan.docx",
                        "lastModifiedDateTime": "2026-05-02T12:00:00Z",
                    },
                ),
                response(200, content=b"document bytes"),
            ]
        )

        result = await self.sharepoint._get_file(http_context(), graph_url("/drives/drive-a/items/item-a"), include_content=True)

        self.assertEqual(
            result,
            {
                "unique_pointer": graph_url("/drives/drive-a/items/item-a"),
                "name": "Plan.docx",
                "size": 128,
                "type": "source_file",
                "source_system": "SharePoint",
                "clickable_url": "https://tenant.sharepoint.com/Plan.docx",
                "file_type": ".docx",
                "file_type_description": "Word document",
                "last_edit_date": "2026-05-02T12:00:00Z",
                "content": base64.b64encode(b"document bytes").decode("utf-8"),
            },
        )

    async def test_get_file_allows_callers_to_omit_last_edit_date(self) -> None:
        """The API endpoint exposes include_last_edit_date for lighter responses."""
        self.sharepoint._request_with_retry = mock.AsyncMock(return_value=response(200, {"name": "notes.md"}))

        result = await self.sharepoint._get_file(
            http_context(),
            graph_url("/drives/drive-a/items/item-a"),
            include_last_edit_date=False,
        )

        self.assertNotIn("last_edit_date", result)

    async def test_get_file_returns_empty_dict_when_metadata_is_unavailable(self) -> None:
        """A missing or forbidden pointer is represented as an empty result."""
        self.sharepoint._request_with_retry = mock.AsyncMock(return_value=response(404))

        self.assertEqual(await self.sharepoint._get_file(http_context(), graph_url("/drives/drive-a/items/missing")), {})

    async def test_fetch_record_content_sets_base64_content_or_none_without_changing_metadata(self) -> None:
        """Streamed records should always keep a predictable content field."""
        successful = {"unique_pointer": graph_url("/drives/drive-a/items/item-a"), "name": "Plan.docx"}
        failed = {"unique_pointer": graph_url("/drives/drive-a/items/item-b"), "name": "Secret.docx"}
        self.sharepoint._request_with_retry = mock.AsyncMock(side_effect=[response(200, content=b"bytes"), response(403)])

        await self.sharepoint._fetch_record_content(http_context(), successful)
        await self.sharepoint._fetch_record_content(http_context(), failed)

        self.assertEqual(successful["content"], base64.b64encode(b"bytes").decode("utf-8"))
        self.assertIsNone(failed["content"])
        self.assertEqual(failed["name"], "Secret.docx")


class TestSharePointStreaming(SharePointTestCase, IsolatedAsyncioTestCase):
    """The stream_files_to_index public contract."""

    async def collect_stream(self, subdata: str | None = None) -> list[dict]:
        """Collect the connector's byte stream into decoded JSON chunks."""
        return [json.loads(chunk.decode("utf-8")) async for chunk in self.sharepoint.stream_files_to_index(subdata, TOKEN)]

    async def test_stream_yields_subdata_header_before_file_records_and_fetches_content(self) -> None:
        """Indexers receive the next delta state first, then fully shaped file records."""
        item = {
            "id": "item-a",
            "name": "Plan.docx",
            "size": 128,
            "webUrl": "https://tenant.sharepoint.com/Plan.docx",
            "lastModifiedDateTime": "2026-05-02T12:00:00Z",
        }
        delta_link = graph_url("/drives/drive-a/root/delta?token=new-token")
        self.sharepoint._collect_drive_tasks = mock.AsyncMock(return_value=[("drive-a", graph_url("/drives/drive-a/root/delta"))])
        self.sharepoint._process_drive = mock.AsyncMock(
            return_value=("drive-a", [self.sharepoint._build_file_record(item, "drive-a")], delta_link)
        )

        def add_content(_ctx: _HttpCtx, record: dict) -> None:
            record["content"] = "base64-content"

        self.sharepoint._fetch_record_content = mock.AsyncMock(side_effect=add_content)
        with mock.patch("interfacer_sharepoint.httpx.AsyncClient", return_value=async_client_context(mock.AsyncMock())):
            chunks = await self.collect_stream()

        self.assertEqual(len(chunks), 2)
        self.assertIn("subdata", chunks[0])
        self.assertEqual(SharePoint._decode_subdata(chunks[0]["subdata"]), {"drive-a": "new-token"})
        self.assertEqual(chunks[1]["name"], "Plan.docx")
        self.assertEqual(chunks[1]["content"], "base64-content")

    async def test_stream_uses_stored_subdata_when_collecting_drive_tasks(self) -> None:
        """Incremental sync state should be decoded before drive tasks are prepared."""
        previous_subdata = SharePoint._encode_subdata({"drive-a": "old-token"})
        self.sharepoint._collect_drive_tasks = mock.AsyncMock(return_value=[])
        self.sharepoint._process_drive = mock.AsyncMock()
        self.sharepoint._fetch_record_content = mock.AsyncMock()

        with mock.patch("interfacer_sharepoint.httpx.AsyncClient", return_value=async_client_context(mock.AsyncMock())):
            chunks = await self.collect_stream(previous_subdata)

        self.assertEqual(len(chunks), 1)
        self.sharepoint._collect_drive_tasks.assert_awaited_once()
        self.assertEqual(self.sharepoint._collect_drive_tasks.await_args.args[1], {"drive-a": "old-token"})

    async def test_stream_skips_failed_drives_and_keeps_successful_drive_delta_tokens(self) -> None:
        """One bad drive should not prevent records or subdata from other drives."""
        good_record = self.sharepoint._build_file_record({"id": "item-a", "name": "ok.pdf"}, "drive-good")
        self.sharepoint._collect_drive_tasks = mock.AsyncMock(
            return_value=[
                ("drive-bad", graph_url("/drives/drive-bad/root/delta")),
                ("drive-good", graph_url("/drives/drive-good/root/delta")),
            ]
        )
        self.sharepoint._process_drive = mock.AsyncMock(
            side_effect=[
                ConnectionError("network failure"),
                ("drive-good", [good_record], graph_url("/drives/drive-good/root/delta?token=good-token")),
            ]
        )

        def add_content(_ctx: _HttpCtx, record: dict) -> None:
            record["content"] = "ok"

        self.sharepoint._fetch_record_content = mock.AsyncMock(side_effect=add_content)

        with mock.patch("interfacer_sharepoint.httpx.AsyncClient", return_value=async_client_context(mock.AsyncMock())):
            chunks = await self.collect_stream()

        self.assertEqual(SharePoint._decode_subdata(chunks[0]["subdata"]), {"drive-good": "good-token"})
        self.assertEqual([chunk["name"] for chunk in chunks[1:]], ["ok.pdf"])

    async def test_process_drive_filters_delta_items_before_streaming(self) -> None:
        """Only real file items are returned from a drive delta page."""
        self.sharepoint._run_delta_query = mock.AsyncMock(
            return_value=(
                [
                    {"id": "folder-a", "name": "Folder", "folder": {}},
                    {"id": "deleted-a", "name": "deleted.pdf", "deleted": {}},
                    {"id": "item-a", "name": "report.pdf"},
                ],
                graph_url("/drives/drive-a/root/delta?token=next"),
            )
        )

        drive_id, records, delta_link = await self.sharepoint._process_drive(
            http_context(),
            "drive-a",
            graph_url("/drives/drive-a/root/delta"),
        )

        self.assertEqual(drive_id, "drive-a")
        self.assertEqual([record["name"] for record in records], ["report.pdf"])
        self.assertEqual(parse_qs(urlparse(delta_link).query)["token"], ["next"])
