"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import os
from urllib.parse import urljoin
import base64
import json
from hashlib import md5
from typing import Any

import requests

from variables import PROJECT, SOURCE_FILE

from unpacker import unpack_values
from logger import dms_error, dms_info


class GitLabs:
    """Gitlabs connector methods."""

    API_URL: str = "api/v4/"
    GIT_BLAME: str = "blame?ref=HEAD"
    GIT_HEAD: str = "?ref=HEAD"

    def __init__(self) -> None:
        """Constructor."""
        address = os.environ.get("GITLAB_ADDRESS")
        self.base = urljoin(str(address), self.API_URL)

    def _get_projects(self) -> dict | list:
        """Retrieve all available projects."""
        url = urljoin(self.base, "projects")
        return self._execute_request(url)

    def get_project_ids(self) -> dict[int, str]:
        """Retrieve a dictionary of IDs for all available projects.

        Returns:
        -------
            Dictionary structured {'id': <HASH_OF_LAST_ACTIVITY_TIMESTAMP>}
        """
        ids: dict[int, str] = {}
        for project in self._get_projects():
            hash_object = md5(project.get("last_activity_at").encode()).hexdigest()
            ids[project.get("id")] = hash_object

        return ids

    def get_projects_as_units(self) -> dict:
        """Retrieve information about available projects."""
        content = self._get_projects()

        projects: dict = {}
        for project in content:
            projects[project.get("web_url")] = {
                "name": unpack_values(project, ("name",)),
                "creator": unpack_values(project, ("namespace", "name")),
                "created_date": unpack_values(project, ("created_at",)),
                "last_edit_date": unpack_values(project, ("last_activity_at",)),
                "type": PROJECT,
            }

        return projects

    def get_files_in_project(self, project_id: int) -> list:
        """Retrieve URLs for all available files in a project.

        Args:
        ----
            project_id: Gitlabs integer value for a specific project.
        """
        tree_args: str = f"projects/{project_id}/repository/tree?recursive=true&per_page=1000&pagination=none"
        url = urljoin(self.base, tree_args)
        content = self._execute_request(url)
        base_path = urljoin(self.base, f"projects/{project_id}/repository/files/")
        files: list = []
        for file in content:
            if file.get("type") == "tree":
                continue
            files.append(urljoin(base_path, file.get("path").replace("/", "%2F")))
        return files

    def get_file(self, url: str, include_content: bool = True) -> dict:
        """

        Args:
        ----
            URL: The URL should be given formatted like:
              https://<GITLABS_DOMAIN>/api/v4/projects/<PROJECT_ID>/repository/files/<FILE_PATH>
            include_content: Determine if actual file content should be included or not.

        """
        file = self._execute_request(urljoin(url, self.GIT_HEAD))
        if isinstance(file, list):
            file = {}
        blame = self._execute_request(urljoin(url.rstrip("/") + "/", self.GIT_BLAME))

        base_structure: dict[Any, Any] = {
            "metadata": {
                "unique_pointer": url,
                "name": file.get("file_name"),
                "size": file.get("size"),
                "last_edit_date": unpack_values(blame, (0, "commit", "committed_date")),
                "type": SOURCE_FILE,
            }
        }

        if include_content:
            base_structure |= {"content": file.get("content")}

        return base_structure

    def pointers_to_all_files_to_index(self, subdata: str | None) -> dict[str, Any]:
        """Retrieve a containing URLs pointing to all available individual files available, except those in projects
            already indexed according to subdata.

        Args:
        ----
            subdata: Data structured: {<Project_ID>: md5(timestamp)} (this data should not be of concern at other layers
                 of the system, but should always be supplied).

        Returns:
        --------
            Dict structure {"subdata": generated_subdata, "file_pointers": file_pointers}, where generated_subdata
                contains is a base64 encoded string of the following {'project_id': 'unique_version_hash'}
                (this should always be passed back by client from previous request).
        """
        subdata_dict: dict

        if subdata is None:
            subdata_dict = {}
        else:
            subdata_dict = json.loads(base64.b64decode(subdata))
        file_pointers: list = []
        project_ids = self.get_project_ids()
        for project_id, change_hash in project_ids.items():
            if change_hash == subdata_dict.get(str(project_id)):
                continue
            file_pointers.extend(self.get_files_in_project(project_id))

        generated_subdata = base64.urlsafe_b64encode(json.dumps(project_ids).encode()).decode()

        return {"subdata": generated_subdata, "file_pointers": file_pointers}

    @staticmethod
    def _execute_request(url: str) -> dict | list:
        """Execute request to supplied URL, JSON content in response expected."""
        try:
            response = requests.get(url)
            content = response.json()
        except requests.exceptions.JSONDecodeError:
            dms_error(f"Gitlab request to {url} could not be decoded.\nExpected JSON structure\nGot {response.text}")
            return {}
        if response.status_code != 200:
            dms_info(f"Request to {url} was made. However, Gitlabs provided a {response.status_code} response.")
        return content
