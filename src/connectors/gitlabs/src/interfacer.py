"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import re
from urllib.parse import urljoin
import base64
import io
from pathlib import Path
import zipfile
from typing import Any
from datetime import datetime, timezone
import binascii
import asyncio
from typing import Generator

import requests #TODO migrate everything away from this.
import httpx

from shared_functions.variables import PROJECT, SOURCE_FILE

from shared_functions.unpacker import unpack_values
from shared_functions.dmis_logger import dms_error, dms_info, dms_warning
from shared_functions.initialisation_tools import read_env_variable
from shared_functions.file_type_logic import get_file_resource, determine_file_type


class GitLabs:
    """Gitlabs connector methods."""

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
        self.source_system = read_env_variable("GITLAB_SYSTEM_NAME")
        address = read_env_variable("GITLAB_ADDRESS")
        self.base = urljoin(f"{address.rstrip("/")}/", self.API_URL)
        file_type_resource = get_file_resource()
        self.file_extensions = [extension.get("extension") for extension in file_type_resource]
        self.extension_descriptions = {extension.get("extension"): extension.get("description") for extension in file_type_resource}

    def _get_projects(self) -> dict | list:
        """Retrieve all available projects."""
        url = urljoin(self.base, "projects")
        projects = self._execute_request(url)
        self.project_information = {
            str(project.get("id")): {
                "web_url": project.get("web_url"),
                "default_branch": project.get("default_branch"),
            }
            for project in projects
        }

        return projects

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

    @staticmethod
    def _get_project_id(url: str) -> None | str:
        """Unsafe parse of API URL to retrieve projectID"""
        pattern = r"https:\/\/([^\/]+)\/api\/v4\/projects\/(\d+)\/repository\/files\/(.+)"
        match = re.match(pattern, url)
        if not match or len(match.groups()) < 3:  # noqa: PLR2004
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
        if self.project_information is None or project_id not in self.project_information:
            self._get_projects()

        project_information = self.project_information.get(project_id)  # type: ignore
        if not isinstance(project_information, dict):
            dms_info(f"Was not able to generate clickable link for {url}")
            return ""
        web_url = project_information.get("web_url")
        default_branch = project_information.get("default_branch")
        return f"{web_url}/-/blob/{default_branch}/{file_path}"

    def get_file(self, url: str, include_content: bool = False, include_last_edit_date: bool = True) -> dict:
        """Retrieve information about file.

        Args:
        ----
            url: The URL should be given formatted like:
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
                self.blame_cache[url] = self._execute_request(url)
            blame = self.blame_cache.get(url)
            if isinstance(blame, list):
                base_structure |= {"last_edit_date": unpack_values(blame, (0, "commit", "committed_date"))}

        file_path = file.get("file_path")
        if isinstance(file_path, str):
            base_structure |= {"clickable_url": self._get_clickable_url(url, file_path)}

        if include_content:
            base_structure |= {"content": file.get("content")}
        return base_structure

    def get_files(self, urls: list, include_content: bool = False, include_last_edit_date: bool = False) -> list:
        """Retrieve wanted information about each file in a list of files.

        Args:
        ----
            urls: The URL should be given formatted like:
              https://<GITLABS_DOMAIN>/api/v4/projects/<PROJECT_ID>/repository/files/<FILE_PATH>
            include_content: Determine if actual file content should be included or not.
            include_last_edit_date: Include last edit date of file.

        """
        files: list = []
        for url in urls:
            files.append(self.get_file(url, include_content, include_last_edit_date))

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
        """."""
        if subdata is None:
            return datetime.min.replace(tzinfo=timezone.utc)

        return self._provided_date(subdata)


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
        files_data: list = []
        latest_update = self._subdata_setup(subdata)
        current_subdata = self.get_project_ids()
        projects = self._get_projects()

        for project in projects:
            project_id = project.get("id")
            new_timestamp = current_subdata.get(project_id)
            if not isinstance(new_timestamp, str):
                continue
            new_timestamp_object = datetime.fromisoformat(new_timestamp.replace("Z", "+00:00"))
            if new_timestamp_object <= latest_update:
                continue
            latest_update = max(latest_update, new_timestamp_object)

            branch = project.get("default_branch")
            url = f"{project.get('web_url')}/-/archive/{branch}/{project.get('path')}-{branch}.zip?ref_type=heads"
            content = requests.get(url, timeout=120).content
            files_data.extend(self._unpack_zip(content, project_id))

        generated_subdata = base64.urlsafe_b64encode(latest_update.isoformat().encode()).decode()

        return {"files": files_data, "subdata": generated_subdata, "index_needed": bool(files_data)}

    async def download_files(self, task_queue, zip_queue):
        """ ."""
        async with httpx.AsyncClient() as client: #TODO, this seems to work
            while True:
                task_data = await task_queue.get()
                if task_data is None:
                    break
                url, project_id = task_data
                async with client.stream("GET", url) as response:
                    data = await response.aread() #TODO ,.content (maybe use .aread())
                    await zip_queue.put({"data": data, "project_id": project_id})
                task_queue.task_done()

    async def unzip_files(self, input_queue, output_queue): #TODO, proj id prob needs to be solved for here.
        """ ."""
        while True:
            input_content = await input_queue.get()
            if input_content is None:
                break
            content = input_content.get("data")
            project_id = input_content.get("project_id")
            unpacked_content = self._unpack_zip(content, project_id)
            await output_queue.put(unpacked_content)
            input_queue.task_done()

    def _project_urls(self, subdata) -> Generator[tuple]:
        """ ."""
        subdata_date = self._subdata_setup(subdata) #THIS is very flawed. 
        current_subdata = self.get_project_ids()
        projects = self._get_projects()

        project_data: list[tuple] = []
        for project in projects:
            project_id = project.get("id")
            new_timestamp = current_subdata.get(project_id)
            if not isinstance(new_timestamp, str):
                continue
            new_timestamp_object = datetime.fromisoformat(new_timestamp.replace("Z", "+00:00"))
            if new_timestamp_object <= subdata_date:
                continue
            new_date = max(subdata_date, new_timestamp_object) #TODO declare this for new subdata
            branch = project.get("default_branch")
            project_data.append((f"{project.get('web_url')}/-/archive/{branch}/{project.get('path')}-{branch}.zip?ref_type=heads", project_id))

        generated_subdata = base64.urlsafe_b64encode(new_date.isoformat().encode()).decode()

        return project_data, generated_subdata


    async def stream_files_to_index(self, subdata: str | None = None):
        """ ."""
        task_queue = asyncio.Queue()
        zip_queue = asyncio.Queue()
        output_queue = asyncio.Queue()

        pointers_to_projects, new_subdata = self._project_urls(subdata)
        for project_pointers in pointers_to_projects:
            await task_queue.put(project_pointers)

        download_tasks: list = [asyncio.create_task(self.download_files(task_queue, zip_queue)) for _ in range(self.NUM_WORKERS)]
        unzip_tasks: list = [asyncio.create_task(self.unzip_files(zip_queue, output_queue)) for _ in range(self.NUM_WORKERS)]

        async def task_producer(): #TODO, could prob migrate a better looking solution
            await task_queue.join()
            for _ in download_tasks:
                await task_queue.put(None)

            await zip_queue.join()
            for _ in unzip_tasks:
                await zip_queue.put(None)

            await output_queue.put(None)

        asyncio.create_task(task_producer())

        while True:
            chunk = await output_queue.get() #TODO define datachunk
            if chunk is None:
                break
            yield chunk

    def check_index_needed(self, subdata: str | None) -> dict[str, Any]:
        """Simple check if reindex is needed based on subdata.

        Args:
        ----
            subdata: Base64 encoded isostructured timestamp.

        Returns:
        --------
            Dict structure {"index_needed": <BOOL>}
        """
        provided_date = self._provided_date(subdata)
        project_ids = self.get_project_ids()

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
        if response.status_code != 200:  # noqa: PLR2004
            dms_info(f"Request to {url} was made. However, Gitlabs provided a {response.status_code} response.")
        return content
