import os
from urllib.parse import urljoin

import requests

from unpacker import unpack_values
from logger import dms_error

class GitLabs:
    API_URL: str = "api/v4/"

    def __init__(self):
        """"""
        self.address = os.environ.get("GITLAB_ADDRESS")

    def get_file_titles():
        pass

    def get_projects(self):
        base = urljoin(self.address, self.API_URL)
        url = urljoin(base, "projects")
        try:
            response = requests.get(url)
            content = response.json()
        except requests.exceptions.JSONDecodeError:
            dms_error(f"Gitlab request to {url} could not be decoded.\nExpected JSON structure\nGot {content}")
            pass

        projects: dict = {}
        for project in content:
            metadata = {"creator": unpack_values(project, ("namespace", "name")),
                        "created_date": unpack_values(project, ("created_at",)),
                        "last_edit_date": unpack_values(project, ("last_activity_at",))
                        }
            projects[project.get("web_url")] = {"name": project.get("name")} | metadata

        return projects
