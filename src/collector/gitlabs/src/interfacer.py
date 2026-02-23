import os
from urllib.parse import urljoin

import requests

from unpacker import unpack_values
from logger import dms_error

from variables import DIRECTORY, PROJECT, SOURCE_FILE

class GitLabs:
    API_URL: str = "api/v4/"

    def __init__(self):
        """"""
        address = os.environ.get("GITLAB_ADDRESS")
        self.base = urljoin(address, self.API_URL)

    def get_files_in_project(self, project_id: int) -> list:
        """"""
        tree_args: str = f"projects/{project_id}/repository/tree?recursive=true&per_page=100&pagination=none"
        url = urljoin(self.base, tree_args)
        content = self.execute_request(url)
        return [file.get("path") for file in content]

    def get_projects(self) -> dict:
        url = urljoin(self.base, "projects")
        content = self.execute_request(url)

        projects: dict = {}
        for project in content:
            projects[project.get("web_url")] = {"name": unpack_values(project, ("name",)),
                        "creator": unpack_values(project, ("namespace", "name")),
                        "created_date": unpack_values(project, ("created_at",)),
                        "last_edit_date": unpack_values(project, ("last_activity_at",)),
                        "type": PROJECT
                        }

        return projects

    @staticmethod
    def execute_request(url: str) -> dict | list:
        """Execute request to supplied URL, JSON content in response expected."""
        try:
            response = requests.get(url)
            content = response.json()
        except requests.exceptions.JSONDecodeError:
            dms_error(f"Gitlab request to {url} could not be decoded.\nExpected JSON structure\nGot {content}")
            return {}

        return content
