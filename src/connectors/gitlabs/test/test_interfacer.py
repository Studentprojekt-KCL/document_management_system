"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from unittest import TestCase, mock

from interfacer import GitLabs


class TestGitLabs(TestCase):
    """Unittests for the GitLabs class instance in Gitlabs connector."""

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

    @mock.patch("interfacer.GitLabs.__init__", return_value=None)
    def setUp(self, _):
        self.instance = GitLabs()
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
            'file_type': '.txt',
            'file_type_description': 'text file'
        }
