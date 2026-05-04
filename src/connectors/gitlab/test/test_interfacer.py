"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import pytest
from unittest import TestCase, mock

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
        self.instance.session = mock_session
        self.instance.file_extensions = [".txt"]
        self.instance.extension_descriptions = {".txt": "text file"}

    async def test_execute_request(self):
        """Test execute_request method."""
        assert await self.instance.execute_get_request(url="", headers={}) == self.CORRECT_DATA

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
