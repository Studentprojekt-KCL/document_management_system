"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import unittest
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

from interfacer import GitLab


class TestGitLab(unittest.IsolatedAsyncioTestCase):
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

    FILE_HEAD_REQUEST = {"x-gitlab-file-name": "test_name.txt", "x-gitlab-size": 0}

    BLAME_DATA = [{"commit": {"committed_date": "1970-01-01T00:00:00.000Z"}}]

    TOKEN_REFRESH = {"client_id": "id",
                "client_secret": "secret",
                    "refresh_token": "token",
"grant_type": "type",
"redirect_uri": "uri"}

    def get_side_effect(self, url: str, *_, **__):
        """Side effect for get method"""
        response_mock = AsyncMock()
        response_mock.status = 200
        if url == "test_url?ref=HEAD":
            response_mock.json = AsyncMock(return_value=self.FILE_DATA)
        elif url == "test_url/blame?ref=HEAD":
            response_mock.json = AsyncMock(return_value=self.BLAME_DATA)
        else:
            response_mock.json = AsyncMock(return_value=self.CORRECT_DATA)

        response = AsyncMock()
        response.__aenter__.return_value = response_mock

        return response

    def head_side_effect(self, url: str, *_, **__):
        """Side effect for head method"""

        response_mock = AsyncMock()
        response_mock.status = 200
        response_mock.raise_for_status.return_value = None

        if url == "test_url?ref=HEAD":
            response_mock.headers = self.FILE_HEAD_REQUEST
        else:
            response_mock.headers = {"": ""}
        cm_mock = MagicMock()
        cm_mock.__aenter__.return_value = response_mock
        cm_mock.__aexit__ = AsyncMock(return_value=None)

        return cm_mock

    def post_side_effect(self, url: str, *_, **__):
        """Side effect for get method"""
        response_mock = AsyncMock()
        response_mock.status = 200
        if "refresh" in url:
            response_mock.json = AsyncMock(return_value=self.TOKEN_REFRESH)
        else: 
            response_mock.json = AsyncMock(return_value={"":""})
        response = AsyncMock()
        response.__aenter__.return_value = response_mock

        return response

    @mock.patch("interfacer.GitLab.__init__", return_value=None)
    def setUp(self, _):
        self.instance = GitLab()
        mock_session = mock.Mock()
        mock_session.get.side_effect = self.get_side_effect
        mock_session.post.side_effect = self.post_side_effect
        mock_session.head.side_effect = self.head_side_effect
        mock_session.closed = False

        self.instance.base = ""
        self.instance.defined_fields = {
            "unique_pointer": None,
            "name": None,
            "size": None,
            "last_edit_date": None,
            "type": None,
            "source_system": None,
            "content": None,
            "file_type": None,
            "file_type_description": None,
        }
        self.instance._session = mock_session
        self.instance.file_extensions = [".txt"]
        self.instance.extension_descriptions = {".txt": "text file"}
        self.instance.source_system = "GitLab"

    async def test_execute_get_request(self):
        """Test execute_request method."""
        assert await self.instance.execute_get_request(url="", headers={}) == self.CORRECT_DATA

    async def test_execute_post_request(self):
        result = await self.instance.execute_post_request(url="refresh", headers={}, data={})
        assert result == self.TOKEN_REFRESH

    async def test_execute_post_request_missing_data_headers(self):
        result = await self.instance.execute_post_request(url="refresh", headers=None, data=None)
        assert result == self.TOKEN_REFRESH

    async def test_get_file(self):
        """Test get_file method."""
        self.instance.source_system = "system"
        result = await self.instance.get_file("test_url", include_content=True)
        assert result == {
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

    async def test_get_file_exclude_content(self):
        """Test get_file method."""
        self.instance.source_system = "system"
        result = await self.instance.get_file("test_url", include_content=False)
        assert result == {'unique_pointer': 'test_url', 'name': 'test_name.txt', 'size': 0, 'last_edit_date': '1970-01-01T00:00:00.000Z', 'type': 'source_file', 'source_system': 'system', 'content': None, 'file_type': '.txt', 'file_type_description': 'text file'}

    def test_projects_to_re_index_not_needed(self):
        projects = {"1": self.CORRECT_DATA}
        subdata = "eyIxIjogIjE5NzAtMDEtMDFUMDA6MDA6MDEuMDAwWiJ9"
        to_index = self.instance._projects_to_re_index(projects=projects, subdata=subdata)
        assert to_index == ([], subdata)

    def test_projects_to_re_index_needed(self):
        projects = {"1": self.CORRECT_DATA[0]}
        subdata = "eyIxIjogIjE5NjktMDctMjBUMDA6MDA6MDEuMDAwWiJ9"
        to_index = self.instance._projects_to_re_index(projects=projects, subdata=subdata)
        assert to_index == ([('/-/archive/main/namespace-main.zip?ref_type=heads', '1')], 'eyIxIjogIjE5NzAtMDEtMDFUMDA6MDA6MDAuMDAwWiJ9')

    def test_generate_subdata(self):
        dates = {"1": "1970-01-01T00:00:00.000Z"}
        assert self.instance._generate_subdata(dates) == "eyIxIjogIjE5NzAtMDEtMDFUMDA6MDA6MDAuMDAwWiJ9"

    def test_parse_subdata(self):
        subdata = "eyIxIjogIjE5NzAtMDEtMDFUMDA6MDA6MDAuMDAwWiJ9"
        assert self.instance._parse_subdata(subdata) == {"1": "1970-01-01T00:00:00.000Z"}

    def test_parse_missing_subdata(self):
        subdata = None
        assert self.instance._parse_subdata(subdata) == {}

    def test_parse_emty_subdata(self):
        subdata = None
        assert self.instance._parse_subdata(subdata) == {}
