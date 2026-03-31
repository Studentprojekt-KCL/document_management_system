"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import os
import re
from urllib.parse import urljoin
import base64
import io
from pathlib import Path
import zipfile
from typing import Any
from datetime import datetime, timezone
import binascii

import requests

from variables import PROJECT, SOURCE_FILE

from unpacker import unpack_values
from dmis_logger import dms_error, dms_info, dms_warning


class GitLabs:
    """Gitlabs connector methods."""

    API_URL: str = "api/v4/"
    GIT_BLAME: str = "blame?ref=HEAD"
    GIT_HEAD: str = "?ref=HEAD"
    session: requests.Session

    def __init__(self) -> None:
        """Constructor."""
        self.session = requests.session()
        address = os.environ.get("GITLAB_ADDRESS")
        if address is None:
            dms_error("Gitlab URL not exported in local environment please export 'GITLAB_ADDRESS'.")
            return
        if not address.endswith("/"):
            address += "/"
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
            last_activity = project.get("last_activity_at")
            if not last_activity:
                continue  # Entails there was no activity for this project
            ids[project.get("id")] = last_activity

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

    @staticmethod
    def _get_project_id(url: str) -> None | str:
        """Unsafe parse of API URL to retrieve projectID"""
        pattern = r"https:\/\/([^\/]+)\/api\/v4\/projects\/(\d+)\/repository\/files\/(.+)"
        match = re.match(pattern, url)
        if not match or len(match.groups()) < 3:
            return None
        return match.group(2)

    def _get_clickable_url(self, url: str, file_path: str) -> str:
        """Retrieve a clickable URL directing to the Gitlab frontend view.

        Note:
            This URL is not directly retrieved from Gitlabs, but rather synthetically constructed.

        Args:
        ----
            url: API URL pointing at a specific file.
            file_path: Precise path to file in project.
        """
        project_id = self._get_project_id(url)
        projects_endpoint = urljoin(self.base, "projects/")
        project_information = self._execute_request(urljoin(projects_endpoint, project_id))
        if isinstance(project_information, list):
            dms_info(f"Was not able to generate clickable link for {url}")
            return ""
        web_url = project_information.get("web_url")
        default_branch = project_information.get("default_branch")
        return f"{web_url}/-/blob/{default_branch}/{file_path}"

    def get_file(self, url: str, include_content: bool = True) -> dict:
        """

        Args:
        ----
            URL: The URL should be given formatted like:
              https://<GITLABS_DOMAIN>/api/v4/projects/<PROJECT_ID>/repository/files/<FILE_PATH>
            include_content: Determine if actual file content should be included or not.

        """
        file: dict | list = {}
        if include_content:
            file = self._execute_request(urljoin(url, self.GIT_HEAD))
        else:
            content = self.session.head(urljoin(url, self.GIT_HEAD)).headers
            file = {
                "file_name": content.get("x-gitlab-file-name"),
                "size": content.get("x-gitlab-size"),
                "file_path": content.get("x-gitlab-file-path"),
            }

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
        file_path = file.get("file_path")
        if isinstance(file_path, str):
            base_structure["metadata"] |= {"clickable_url": self._get_clickable_url(url, file_path)}

        if include_content:
            base_structure |= {"content": file.get("content")}

        return base_structure

    def _unpack_zip(self, content: bytes, project_id: int) -> list:
        """Unpack .zip content and return a list containing all the files."""
        base_path = urljoin(self.base, f"projects/{project_id}/repository/files/")

        files_data: list = []
        with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
            for file in zip_file.namelist():
                file_path = Path(file)
                intermediate_path = str(Path(*file_path.parts[1:]))
                info = zip_file.getinfo(file)
                if info.is_dir():
                    continue
                try:
                    file_content = zip_file.read(file).decode("utf-8")
                except UnicodeDecodeError as err:
                    file_content = ""
                    dms_warning(f"Could not decode file: {file}. {err}")
                files_data.append(
                    {
                        "content": base64.b64encode(file_content.encode("utf-8")).decode("utf-8"),
                        "metadata": {
                            "name": file_path.name,
                            "unique_pointer": urljoin(base_path, intermediate_path.replace("/", "%2F")),
                            "size": info.file_size,
                        },
                    }
                )

        return files_data

    def files_to_index(self, subdata: str | None = None) -> dict:
        """Retrieve a structure of files to index.

        Args:
        ----
            subdata: Data structured: {<Project_ID>: md5(timestamp)} (this data should not be of concern at other layers
                 of the system, but should always be supplied).

        Returns:
        -------
            Dict structure {"subdata": generated_subdata, "files": file_data}, where generated_subdata
                contains is a base64 encoded string of the following {'project_id': 'unique_version_hash'}
                (this should always be passed back by client from previous request).
        """
        provided_date: datetime = self._provided_date(subdata)
        files_data: list = []

        current_subdata = self.get_project_ids()
        projects = self._get_projects()

        latest_update = datetime.min.replace(tzinfo=timezone.utc)
        for project in projects:
            project_id = project.get("id")
            new_timestamp = current_subdata.get(project_id)
            if not isinstance(new_timestamp, str):
                continue
            new_timestamp_object = datetime.fromisoformat(new_timestamp.replace("Z", "+00:00"))
            if new_timestamp_object <= provided_date:
                continue
            latest_update = max(latest_update, new_timestamp_object)

            branch = project.get("default_branch")
            url = f"{project.get('web_url')}/-/archive/{branch}/{project.get('path')}-{branch}.zip?ref_type=heads"
            content = requests.get(url, timeout=120).content
            files_data.extend(self._unpack_zip(content, project_id))

        generated_subdata = base64.urlsafe_b64encode(latest_update.isoformat().encode()).decode()

        return {"files": files_data, "subdata": generated_subdata}

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
        provided_date = self._provided_date(subdata)

        file_pointers: list = []
        project_ids = self.get_project_ids()
        latest_update = datetime.min.replace(tzinfo=timezone.utc)
        for project_id, change_time in project_ids.items():
            if not isinstance(change_time, str):
                continue
            new_timestamp_object = datetime.fromisoformat(change_time.replace("Z", "+00:00"))
            if new_timestamp_object <= provided_date:
                continue
            latest_update = max(latest_update, new_timestamp_object)

            file_pointers.extend(self.get_files_in_project(project_id))

        generated_subdata = base64.urlsafe_b64encode(latest_update.isoformat().encode()).decode()

        return {"subdata": generated_subdata, "file_pointers": file_pointers}

    @staticmethod
    def _provided_date(subdata: str | None) -> datetime:
        """Parse string dateobject from iso format to datetime object."""
        if subdata is not None:
            try:
                subdata_bytes = base64.b64decode(subdata)
            except binascii.Error:
                dms_info("Request with invalid base64 encoding made to Gitlab connector: %s", subdata)
            subdata_str = subdata_bytes.decode("utf-8")
            try:
                return datetime.fromisoformat(subdata_str.replace("Z", "+00:00"))
            except ValueError:
                dms_error("Gitlab connector could not interpret subdata: %s", subdata)
        return datetime.min.replace(tzinfo=timezone.utc)

    def _execute_request(self, url: str) -> dict | list:
        """Execute request to supplied URL, JSON content in response expected."""
        try:
            response = self.session.get(url, timeout=120)
            content = response.json()
        except requests.exceptions.JSONDecodeError:
            dms_warning(f"Gitlab request to {url} could not be decoded.\nExpected JSON structure\nGot {response.text}")
            return {}
        except requests.exceptions.MissingSchema as err:
            dms_error(f"Gitlab URL incorrectly formatted, please export 'GITLAB_ADDRESS'. (From error: {err})")
        if response.status_code != 200:
            dms_info(f"Request to {url} was made. However, Gitlabs provided a {response.status_code} response.")
        return content
