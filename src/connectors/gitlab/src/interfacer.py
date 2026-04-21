"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import re
from urllib.parse import urljoin
import base64
import json
import io
from pathlib import Path
import zipfile
from typing import Any
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import binascii
import asyncio

import requests
import httpx

from shared_functions.variables import SOURCE_FILE
from shared_functions.unpacker import unpack_values
from shared_functions.dmis_logger import dms_error, dms_info, dms_warning
from shared_functions.initialisation_tools import read_env_variable
from shared_functions.file_type_logic import get_file_resource, determine_file_type


class GitLab:
    """Gitlab connector methods."""

    API_URL: str = "api/v4/"
    GIT_BLAME: str = "blame?ref=HEAD"
    GIT_HEAD: str = "?ref=HEAD"
    NUM_WORKERS: int = 10
    session: requests.Session
    source_system: str
    project_information: dict | None = None
    blame_cache: dict = {}
    file_extensions: list = []
    extension_descriptions: dict = {}

    def __init__(self) -> None:
        """Constructor."""
        self.session = requests.session()
        self.source_system = read_env_variable("CONGITLAB_SYSTEM_NAME")
        address = read_env_variable("CONGITLAB_GITLAB_URL")
        self.base = urljoin(f"{address.rstrip("/")}/", self.API_URL)
        file_type_resource = get_file_resource()
        self.file_extensions = [extension.get("extension") for extension in file_type_resource]
        self.extension_descriptions = {extension.get("extension"): extension.get("description") for extension in file_type_resource}

    @staticmethod
    def _construct_request_headers(bearer_token: str | None = None) -> dict:
        if isinstance(bearer_token, str):
            return {"Authorization": f"Bearer {bearer_token}"}
        return {}

    def _get_projects(self, bearer_token: str | None = None) -> dict | list:
        """Retrieve all available projects."""
        url = urljoin(self.base, "projects")
        projects = self._execute_get_request(url, self._construct_request_headers(bearer_token))
        self.project_information = {
            str(project.get("id")): {
                "web_url": project.get("web_url"),
                "default_branch": project.get("default_branch"),
            }
            for project in projects
        }

        return projects

    def get_project_ids(self, bearer_token: str | None = None) -> dict[int, str]:
        """Retrieve a dictionary of IDs for all available projects.

        Returns:
        -------
            Dictionary structured {'id': <HASH_OF_LAST_ACTIVITY_TIMESTAMP>}
        """
        ids: dict[int, str] = {}
        for project in self._get_projects(bearer_token):
            last_activity = project.get("last_activity_at")
            if not last_activity:
                continue  # Entails there was no activity for this project
            ids[project.get("id")] = last_activity

        return ids

    @staticmethod
    def _get_project_id(url: str) -> None | str:
        """Unsafe parse of API URL to retrieve projectID"""
        pattern = r"https:\/\/([^\/]+)\/api\/v4\/projects\/(\d+)\/repository\/files\/(.+)"
        match = re.match(pattern, url)
        if not match or len(match.groups()) < 3:  # noqa: PLR2004
            return None
        return match.group(2)

    def _get_clickable_url(self, url: str, file_path: str, bearer_token: str | None = None) -> str:
        """Retrieve a clickable URL directing to the Gitlab frontend view.

        Note:
            This URL is not directly retrieved from Gitlab, but rather synthetically constructed.

        Args:
        ----
            url: API URL pointing at a specific file.
            file_path: Precise path to file in project.
            bearer_token: A valid bearer GitLab token or None.
        """
        project_id = self._get_project_id(url)
        if self.project_information is None or project_id not in self.project_information:
            self._get_projects(bearer_token)

        project_information = self.project_information.get(project_id)  # type: ignore
        if not isinstance(project_information, dict):
            dms_info(f"Was not able to generate clickable link for {url}")
            return ""
        web_url = project_information.get("web_url")
        default_branch = project_information.get("default_branch")
        return f"{web_url}/-/blob/{default_branch}/{file_path}"

    def get_file(
        self, url: str, bearer_token: str | None = None, include_content: bool = False, include_last_edit_date: bool = True
    ) -> dict:
        """Retrieve information about file.

        Args:
        ----
            url: The URL should be given formatted like:
              https://<GITLAB_DOMAIN>/api/v4/projects/<PROJECT_ID>/repository/files/<FILE_PATH>
            include_content: Determine if actual file content should be included or not.
            bearer_token: A valid bearer GitLab token or None.

        """
        file: dict | list = {}
        if include_content:
            file = self._execute_get_request(urljoin(url, self.GIT_HEAD), self._construct_request_headers(bearer_token))
        else:
            content: dict = self._execute_head_request(urljoin(url, self.GIT_HEAD), self._construct_request_headers(bearer_token))
            lower_content = {key.lower(): value for key, value in content.items()}
            file_name_str = lower_content.get("x-gitlab-file-name")
            file_path_str = lower_content.get("x-gitlab-file-path")
            if isinstance(file_name_str, str):
                file_name_str = file_name_str.encode("iso-8859-1").decode("utf-8")
            if isinstance(file_path_str, str):
                file_path_str = file_path_str.encode("iso-8859-1").decode("utf-8")
            file = {
                "file_name": file_name_str,
                "size": lower_content.get("x-gitlab-size"),
                "file_path": file_path_str,
            }
        if isinstance(file, list):
            file = {}

        file_name: str | None = file.get("file_name")
        extension: dict = determine_file_type(file_name, self.file_extensions, self.extension_descriptions)
        base_structure: dict[Any, Any] = {
            "unique_pointer": url,
            "name": file_name,
            "size": file.get("size"),
            "type": SOURCE_FILE,
            "source_system": self.source_system,
        } | extension

        if include_last_edit_date:
            url = urljoin(url.rstrip("/") + "/", self.GIT_BLAME)
            if url not in self.blame_cache:
                self.blame_cache[url] = self._execute_get_request(url, self._construct_request_headers(bearer_token))
            blame = self.blame_cache.get(url)
            if isinstance(blame, list):
                base_structure |= {"last_edit_date": unpack_values(blame, (0, "commit", "committed_date"))}

        file_path = file.get("file_path")
        if isinstance(file_path, str):
            base_structure |= {"clickable_url": self._get_clickable_url(url, file_path)}

        if include_content:
            base_structure |= {"content": file.get("content")}
        return base_structure

    def get_files(
        self, urls: list, bearer_token: str | None = None, include_content: bool = False, include_last_edit_date: bool = False
    ) -> list:
        """Retrieve wanted information about each file in a list of files.

        Args:
        ----
            urls: The URL should be given formatted like:
              https://<GITLAB_DOMAIN>/api/v4/projects/<PROJECT_ID>/repository/files/<FILE_PATH>
            include_content: Determine if actual file content should be included or not.
            include_last_edit_date: Include last edit date of file.
            bearer_token: A valid bearer GitLab token or None.

        """
        files: list = []
        for url in urls:
            files.append(self.get_file(url, bearer_token, include_content, include_last_edit_date))

        return files

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
                    dms_info(f"Could not decode file: {file}. {err}")
                file_name = file_path.name
                extension: dict = determine_file_type(file_name, self.file_extensions, self.extension_descriptions)
                files_data.append(
                    {
                        "content": base64.b64encode(file_content.encode("utf-8")).decode("utf-8"),
                        "metadata": {
                            "name": file_name,
                            "unique_pointer": urljoin(base_path, intermediate_path.replace("/", "%2F")),
                            "size": info.file_size,
                        }
                        | extension,
                    }
                )

        return files_data

    def _subdata_setup(self, subdata: str | None = None) -> datetime:
        """Set up subdata, either by parsind data, or if None, return datatime.min data."""
        if subdata is None:
            return datetime.min.replace(tzinfo=timezone.utc)

        return self._provided_date(subdata)

    def _project_urls(self, subdata: str | None = None, bearer_token: str | None = None) -> tuple[list, str]:
        """Retrieve a structure of files to index."""

        subdata_date = self._subdata_setup(subdata)
        current_subdata = self.get_project_ids()
        projects = self._get_projects(bearer_token)
        new_date = subdata_date

        project_data: list[tuple] = []
        for project in projects:
            project_id = project.get("id")
            new_timestamp = current_subdata.get(project_id)
            if not isinstance(new_timestamp, str):
                continue
            new_timestamp_object = datetime.fromisoformat(new_timestamp.replace("Z", "+00:00"))
            if new_timestamp_object <= subdata_date:
                continue
            new_date = max(new_date, new_timestamp_object)
            branch = project.get("default_branch")
            project_data.append(
                (f"{project.get('web_url')}/-/archive/{branch}/{project.get('path')}-{branch}.zip?ref_type=heads", project_id)
            )

        generated_subdata = base64.urlsafe_b64encode(new_date.isoformat().encode()).decode()

        return project_data, generated_subdata

    def files_to_index(self, subdata: str | None = None, bearer_token: str | None = None) -> dict:
        """Retrieve a structure of files to index.

        Args:
        ----
            subdata: Base64 encoded isostructured timestamp.
            bearer_token: A valid bearer GitLab token or None.

        Returns:
        -------
            Dict structure {"subdata": generated_subdata, "files": file_data, "index_needed":
              <BOOL INDICATIANG IF REINDEX IS NEEED>}
        """
        files_data: list = []
        pointers_to_projects, generated_subdata = self._project_urls(subdata, bearer_token)

        for project_pointers in pointers_to_projects:
            url, project_id = project_pointers
            content = requests.get(url, timeout=120).content
            files_data.extend(self._unpack_zip(content, project_id))

        return {"files": files_data, "subdata": generated_subdata, "index_needed": bool(files_data)}

    async def _download_files(self, task_queue: asyncio.Queue, zip_queue: asyncio.Queue) -> None:
        """Download all artifacts from tast_queue and put in zip_queue."""
        async with httpx.AsyncClient() as client:
            while True:
                task_data = await task_queue.get()
                if task_data is None:
                    break
                url, project_id = task_data
                async with client.stream("GET", url) as response:
                    data = await response.aread()
                    await zip_queue.put({"data": data, "project_id": project_id})
                task_queue.task_done()

    async def unzip_files(self, input_queue: asyncio.Queue, output_queue: asyncio.Queue) -> None:
        """Unzip all files in input queue and put content in output queue."""
        while True:
            input_content = await input_queue.get()
            if input_content is None:
                break
            content = input_content.get("data")
            project_id = input_content.get("project_id")
            unpacked_content = self._unpack_zip(content, project_id)
            await output_queue.put(unpacked_content)
            input_queue.task_done()

    async def stream_files_to_index(self, subdata: str | None = None, bearer_token: str | None = None) -> AsyncGenerator[bytes]:
        """Streaming for files to index.

        Args:
        ----
            subdata: Base64 encoded isostructured timestamp.
            bearer_token: A valid bearer GitLab token or None.
        """
        task_queue: asyncio.Queue = asyncio.Queue()
        zip_queue: asyncio.Queue = asyncio.Queue()
        output_queue: asyncio.Queue = asyncio.Queue()

        pointers_to_projects, new_subdata = self._project_urls(subdata, bearer_token)
        for project_pointers in pointers_to_projects:
            await task_queue.put(project_pointers)

        download_tasks: list = [asyncio.create_task(self._download_files(task_queue, zip_queue)) for _ in range(self.NUM_WORKERS)]
        unzip_tasks: list = [asyncio.create_task(self.unzip_files(zip_queue, output_queue)) for _ in range(self.NUM_WORKERS)]

        async def producer() -> None:
            """Shutdown signaling to each worker defined in stream_files_to_index."""
            await task_queue.join()
            for _ in download_tasks:
                await task_queue.put(None)

            await zip_queue.join()
            for _ in unzip_tasks:
                await zip_queue.put(None)

            await output_queue.put(None)

        asyncio.create_task(producer())

        yield json.dumps({"subdata": new_subdata}).encode("utf-8")

        while True:
            chunk = await output_queue.get()
            if chunk is None:
                break
            for file in chunk:
                yield json.dumps(file).encode("utf-8")

    def check_index_needed(self, subdata: str | None, bearer_token: str | None = None) -> dict[str, Any]:
        """Simple check if reindex is needed based on subdata.

        Args:
        ----
            subdata: Base64 encoded isostructured timestamp.
            bearer_token: A valid bearer GitLab token or None.

        Returns:
        --------
            Dict structure {"index_needed": <BOOL>}
        """
        provided_date = self._provided_date(subdata)
        project_ids = self.get_project_ids(bearer_token)

        for change_time in project_ids.values():
            if not isinstance(change_time, str):
                continue
            new_timestamp_object = datetime.fromisoformat(change_time.replace("Z", "+00:00"))
            if new_timestamp_object <= provided_date:
                continue
            return {"index_needed": True}

        return {"index_needed": False}

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

    def _execute_get_request(self, url: str, headers: dict) -> dict | list:
        """Execute GET request to supplied URL, JSON content in response expected."""
        try:
            response = self.session.get(url, timeout=120, headers=headers)
            content = response.json()
        except requests.exceptions.JSONDecodeError:
            dms_warning(f"Gitlab request to {url} could not be decoded.\nExpected JSON structure\nGot {response.text}")
            return {}
        except requests.exceptions.MissingSchema as err:
            dms_error(f"Gitlab URL incorrectly formatted, please export 'CONGITLAB_GITLAB_URL'. (From error: {err})")
        if response.status_code != 200:  # noqa: PLR2004
            dms_info(f"Request to {url} was made. However, Gitlab provided a {response.status_code} response.")
        return content

    def _execute_head_request(self, url: str, headers: dict) -> dict:
        """Execute HEAD request to supplied URL."""
        try:
            content = self.session.head(url, headers=headers)
            content.raise_for_status()
        except requests.exceptions.MissingSchema as err:
            dms_error(f"Gitlab URL incorrectly formatted, please export 'CONGITLAB_GITLAB_URL'. (From error: {err})")
        except requests.HTTPError:
            dms_info(f"Unable to access object expected to exist at: {url}. (Got status code {content.status_code})")
            return {}
        return dict(content.headers)
