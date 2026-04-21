"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import asyncio
import base64
import io
import json
import zipfile
from unittest import TestCase, mock
from unittest.mock import AsyncMock, MagicMock

import httpx

from interfacer import GitLab


class TestGitLab(TestCase):
    """Unittests for the GitLab class instance in Gitlab connector."""

    CORRECT_DATA = [
        {
            "id": 1,
            "description": "test description",
            "name": "test_name",
            "name_with_namespace": "namespace",
            "path": "namespace",
            "path_with_namespace": "namespace",
            "created_at": "1970-01-01T00:00:00.000Z",
            "default_branch": "main",
            "tag_list": [],
            "topics": [],
            "ssh_url_to_repo": "",
            "http_url_to_repo": "",
            "web_url": "",
            "readme_url": "",
            "forks_count": 0,
            "avatar_url": None,
            "star_count": 0,
            "last_activity_at": "1970-01-01T00:00:00.000Z",
            "visibility": "public",
            "namespace": {
                "id": 0,
                "name": "user",
                "path": "username",
                "kind": "user",
                "full_path": "user",
                "parent_id": None,
                "avatar_url": "",
                "web_url": "",
            },
        }
    ]

    FILE_DATA = {"file_name": "test_file.txt", "size": 0, "content": "unittest"}

    BLAME_DATA = [{"commit": {"committed_date": "1970-01-01T00:00:00.000Z"}}]

    def get_side_effect(self, url: str, *_, **__):
        """Side effect for get method"""
        response_mock = mock.Mock()
        if url == "test_url?ref=HEAD":
            response_mock.json.return_value = self.FILE_DATA
        elif url == "test_url/blame?ref=HEAD":
            response_mock.json.return_value = self.BLAME_DATA
        else:
            response_mock.json.return_value = self.CORRECT_DATA
        return response_mock

    @mock.patch("interfacer.GitLab.__init__", return_value=None)
    def setUp(self, _):
        self.instance = GitLab()
        mock_session = mock.Mock()
        mock_session.get.side_effect = self.get_side_effect
        self.instance.base = ""
        self.instance.session = mock_session
        self.instance.file_extensions = [".txt"]
        self.instance.extension_descriptions = {".txt": "text file"}

    def test_execute_request(self):
        """Test _execute_request method."""
        assert self.instance._execute_request(url="") == self.CORRECT_DATA

    def test_check_index_needed_no_sudata(self):
        """Test check_index_needed method without current subdata."""
        pointers = self.instance.check_index_needed(None)
        assert "index_needed" in pointers.keys()
        assert pointers.get("index_needed") == True

    def test_check_index_needed_false(self):
        """Test check_index_needed method with current subdata."""
        pointers = self.instance.check_index_needed("MTk3MC0wMS0wMVQwMDowMDowMC4wMDBa")
        assert pointers.get("index_needed") == False

    def test_check_index_needed_old_subdata(self):
        """Test check_index_needed method with old subdata."""
        pointers = self.instance.check_index_needed("MTk2OC0wMS0wMVQwMDowMDowMC4wMDBa")
        assert pointers.get("index_needed") == True

    def test_get_file(self):
        """Test get_file method."""
        self.instance.source_system = "system"
        print(self.instance.get_file("test_url", True))
        assert self.instance.get_file("test_url", True) == {
            "unique_pointer": "test_url",
            "name": "test_file.txt",
            "size": 0,
            "last_edit_date": "1970-01-01T00:00:00.000Z",
            "type": "source_file",
            "source_system": "system",
            "content": "unittest",
            "file_type": ".txt",
            "file_type_description": "text file",
        }


def _make_zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    return buf.getvalue()


def _fake_stream_client(zip_bytes: bytes) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.aread = AsyncMock(return_value=zip_bytes)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    client = MagicMock()
    client.stream.return_value = response
    client.aclose = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class TestGitLabStreaming(TestCase):
    """Tests for the async streaming path in GitLab connector."""

    _SUBDATA_NEW = base64.urlsafe_b64encode("2026-03-01T00:00:00+00:00".encode()).decode()
    _SUBDATA_OLD = base64.urlsafe_b64encode("2026-04-01T00:00:00+00:00".encode()).decode()
    _PROJECT_URLS_RESULT = (
        [("https://gitlab.test/owner/repo/-/archive/main/repo-main.zip", 1)],
        _SUBDATA_NEW,
    )
    _EMPTY_PROJECT_URLS_RESULT = ([], _SUBDATA_OLD)

    @mock.patch("interfacer.GitLab.__init__", return_value=None)
    def setUp(self, _):
        self.instance = GitLab()
        self.instance.request_timeout = 30
        self.instance.shared_client = True
        self.instance.base = "http://gitlab.test/api/v4/"
        self.instance.file_extensions = [".py"]
        self.instance.extension_descriptions = {".py": "Python source"}

    def _collect(self, gen) -> list[dict]:
        async def run():
            return [json.loads(chunk) async for chunk in gen]

        return asyncio.run(run())

    def test_stream_yields_subdata_then_files(self):
        """First chunk is the subdata header; subsequent chunks are file objects."""
        zip_bytes = _make_zip({"repo-main/src/file.py": "print('hello')"})
        self.instance._project_urls = lambda _=None: self._PROJECT_URLS_RESULT
        with mock.patch("interfacer.httpx.AsyncClient", return_value=_fake_stream_client(zip_bytes)):
            chunks = self._collect(self.instance.stream_files_to_index())
        self.assertIn("subdata", chunks[0])
        self.assertGreater(len(chunks), 1)
        self.assertIn("content", chunks[1])
        self.assertIn("metadata", chunks[1])

    def test_stream_filters_old_projects(self):
        """Projects with activity before subdata timestamp produce no file chunks."""
        self.instance._project_urls = lambda _=None: self._EMPTY_PROJECT_URLS_RESULT
        chunks = self._collect(self.instance.stream_files_to_index(subdata=self._SUBDATA_OLD))
        self.assertEqual(len(chunks), 1)
        self.assertIn("subdata", chunks[0])

    def test_stream_per_worker_client(self):
        """With shared_client=False workers each create their own client and streaming still works."""
        self.instance.shared_client = False
        zip_bytes = _make_zip({"repo-main/file.py": "x"})
        self.instance._project_urls = lambda _=None: self._PROJECT_URLS_RESULT
        with mock.patch("interfacer.httpx.AsyncClient", return_value=_fake_stream_client(zip_bytes)):
            chunks = self._collect(self.instance.stream_files_to_index())
        self.assertIn("subdata", chunks[0])
        self.assertGreater(len(chunks), 1)

    def test_http_client_shared_yields_client(self):
        """_http_client yields an AsyncClient instance when shared_client=True."""
        self.instance.shared_client = True

        async def run():
            async with self.instance._http_client() as client:
                return client

        result = asyncio.run(run())
        self.assertIsInstance(result, httpx.AsyncClient)

    def test_http_client_per_worker_yields_none(self):
        """_http_client yields None when shared_client=False."""
        self.instance.shared_client = False

        async def run():
            async with self.instance._http_client() as client:
                return client

        self.assertIsNone(asyncio.run(run()))

    def test_task_done_called_on_download_error(self):
        """task_done() is called in finally even when a download raises httpx.HTTPError."""

        async def run():
            task_queue: asyncio.Queue = asyncio.Queue()
            zip_queue: asyncio.Queue = asyncio.Queue()
            await task_queue.put(("https://gitlab.test/repo.zip", 1))
            await task_queue.put(None)
            client = MagicMock()
            client.stream.side_effect = httpx.HTTPError("connection error")
            await self.instance._download_files(task_queue, zip_queue, client)
            await asyncio.wait_for(task_queue.join(), timeout=1.0)

        asyncio.run(run())

    def test_unzip_files_uses_to_thread(self):
        """unzip_files must run _unpack_zip via asyncio.to_thread, not block the event loop."""
        fake_files = [{"content": "x", "metadata": {"name": "f.py"}}]

        async def run():
            zip_queue: asyncio.Queue = asyncio.Queue()
            output_queue: asyncio.Queue = asyncio.Queue()
            await zip_queue.put({"data": b"zip", "project_id": 1})
            await zip_queue.put(None)
            with mock.patch("interfacer.asyncio.to_thread", new=AsyncMock(return_value=fake_files)):
                await self.instance.unzip_files(zip_queue, output_queue)
            return await output_queue.get()

        result = asyncio.run(run())
        self.assertEqual(result, fake_files)

    def test_project_urls_called_via_to_thread(self):
        """stream_files_to_index delegates _project_urls to asyncio.to_thread."""
        self.instance._project_urls = lambda _=None: self._EMPTY_PROJECT_URLS_RESULT

        async def passthrough(fn, *args):
            return fn(*args)

        async def run():
            with mock.patch("interfacer.asyncio.to_thread", side_effect=passthrough) as mock_thread:
                async for _ in self.instance.stream_files_to_index():
                    pass
                return mock_thread.call_args_list

        calls = asyncio.run(run())
        first_fn = calls[0][0][0]
        self.assertEqual(first_fn, self.instance._project_urls)
