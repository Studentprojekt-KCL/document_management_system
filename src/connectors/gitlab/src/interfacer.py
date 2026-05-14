"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import re
from urllib.parse import urljoin
import base64
import json
import io
from pathlib import Path
import zipfile
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import binascii
import asyncio
import copy

import aiohttp

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
    _session: aiohttp.ClientSession | None
    source_system: str
    project_information: dict | None = None
    blame_cache: dict = {}
    file_extensions: list = []
    extension_descriptions: dict = {}
    defined_fields: dict

    def __init__(self, address: str) -> None:
        """Constructor."""
        self._session = None
        self.source_system = read_env_variable("CONGITLAB_SYSTEM_NAME")
        self.base = urljoin(f"{address.rstrip("/")}/", self.API_URL)
        file_type_resource = get_file_resource()
        self.file_extensions = [extension.get("extension") for extension in file_type_resource]
        self.extension_descriptions = {extension.get("extension"): extension.get("description") for extension in file_type_resource}

        self.defined_fields = {"content": None, "name": None, "unique_pointer": None, "size": None, "source_system": None} | {
            key: None for key in determine_file_type("", self.file_extensions, self.extension_descriptions)
        }

    async def get_session(self) -> aiohttp.ClientSession:
        """Set up AIO http clinet if not initialized."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close_session(self) -> None:
        """Tear down session."""
        if self._session is not None:
            self._session.close()

    @staticmethod
    def _construct_request_headers(bearer_token: str | None = None) -> dict:
        if isinstance(bearer_token, str):
            return {"Authorization": f"Bearer {bearer_token}"}
        return {}

    async def _get_projects(self, bearer_token: str | None = None) -> dict:
        """Retrieve all available projects."""
        url = urljoin(self.base, "projects")
        projects = await self.execute_get_request(url, self._construct_request_headers(bearer_token))
        self.project_information = {
            str(project.get("id")): {
                "web_url": project.get("web_url"),
                "default_branch": project.get("default_branch"),
            }
            for project in projects
        }
        # NOTE could probably be done better, just need to get it running.
        projects_dict = {str(project.get("id")): project for project in projects}

        if isinstance(projects_dict, dict):
            return projects_dict
        return {}

    @staticmethod
    def _get_project_id(url: str) -> None | str:
        """Unsafe parse of API URL to retrieve projectID"""
        pattern = r"https:\/\/([^\/]+)\/api\/v4\/projects\/(\d+)\/repository\/files\/(.+)"
        match = re.match(pattern, url)
        if not match or len(match.groups()) < 3:  # noqa: PLR2004
            return None
        return match.group(2)

    async def _get_clickable_url(self, url: str, file_path: str, bearer_token: str | None = None) -> str:
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
            await self._get_projects(bearer_token)

        if not isinstance(self.project_information, dict):
            dms_info(f"Was not able to generate clickable link for {url}")
            return ""
        project_information = self.project_information.get(project_id)

        if not isinstance(project_information, dict):
            dms_info(f"Was not able to generate clickable link for {url}")
            return ""
        web_url = project_information.get("web_url")
        default_branch = project_information.get("default_branch")
        return f"{web_url}/-/blob/{default_branch}/{file_path}"

    async def get_file(
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
            file = await self.execute_get_request(urljoin(url, self.GIT_HEAD), self._construct_request_headers(bearer_token))
        else:
            content: dict = await self.execute_head_request(
                urljoin(url, self.GIT_HEAD), self._construct_request_headers(bearer_token)
            )
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
        base_structure = copy.deepcopy(self.defined_fields)
        base_structure |= {
            "unique_pointer": url,
            "name": file_name,
            "size": file.get("size"),
            "type": SOURCE_FILE,
            "source_system": self.source_system,
        } | extension

        if include_last_edit_date:
            url = urljoin(url.rstrip("/") + "/", self.GIT_BLAME)
            if url not in self.blame_cache:
                self.blame_cache[url] = await self.execute_get_request(url, self._construct_request_headers(bearer_token))
            blame = self.blame_cache.get(url)
            if isinstance(blame, list):
                base_structure |= {"last_edit_date": unpack_values(blame, (0, "commit", "committed_date"))}

        file_path = file.get("file_path")
        if isinstance(file_path, str):
            base_structure |= {"clickable_url": await self._get_clickable_url(url, file_path)}

        if include_content:
            base_structure |= {"content": file.get("content")}
        return base_structure

    async def get_files(
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
            files.append(await self.get_file(url, bearer_token, include_content, include_last_edit_date))

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
                file_content = zip_file.read(file)
                file_name = file_path.name
                extension: dict = determine_file_type(file_name, self.file_extensions, self.extension_descriptions)
                base_structure = copy.deepcopy(self.defined_fields)
                base_structure |= {
                    "content": base64.b64encode(file_content).decode("utf-8"),
                    "unique_pointer": urljoin(base_path, intermediate_path.replace("/", "%2F")),
                    "name": file_name,
                    "size": info.file_size,
                    "type": SOURCE_FILE,
                    "source_system": self.source_system,
                } | extension
                files_data.append(base_structure)

        return files_data

    @staticmethod
    def _create_date_object(date_string: str) -> datetime:
        """Generate datetime object from string and set UTC timezone."""
        date = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date

    @staticmethod
    def _parse_subdata(subdata: str | None) -> dict:
        """Parse string dateobject from iso format to datetime object."""
        if subdata is None:
            return {}

        try:
            subdata_bytes = base64.b64decode(subdata)
        except binascii.Error:
            dms_warning("Request where subdata was invalid base64 encoding made to Gitlab connector: %s", subdata)
            return {}
        subdata_str = subdata_bytes.decode("utf-8")

        try:
            return json.loads(subdata_str)
        except json.decoder.JSONDecodeError:
            dms_warning("Request where decoded subdata was invalid json structure made to Gitlab connector: %s", subdata_str)
            return {}

    @staticmethod
    def _generate_subdata(new_subdata: dict) -> str:
        """Generate base64 encoded subdata from dict."""
        return base64.urlsafe_b64encode(json.dumps(new_subdata).encode("utf-8")).decode()

    def _projects_to_re_index(self, projects: dict[str, dict], subdata: str | None = None) -> tuple[list, str]:
        """Determine project needing to be reindexed, together with new subdata."""
        projects_to_index: list = []
        subdata_dict = self._parse_subdata(subdata)
        new_subdata: dict = subdata_dict
        for project_id, project in projects.items():
            if not isinstance(project, dict):
                continue
            subdata_project = subdata_dict.get(project_id)
            branch = project.get("default_branch")
            edit_date = project.get("last_activity_at")
            if not isinstance(subdata_project, str):
                projects_to_index.append(
                    (f"{project.get('web_url')}/-/archive/{branch}/{project.get('path')}-{branch}.zip?ref_type=heads", project_id)
                )
                new_subdata[project_id] = edit_date
                continue
            if edit_date is None:  # quick fix dont know if this is wanted behaviour.
                continue
            subdata_date_object = self._create_date_object(subdata_project)
            edit_date_object = self._create_date_object(edit_date)
            if edit_date_object > subdata_date_object:
                projects_to_index.append(
                    (f"{project.get('web_url')}/-/archive/{branch}/{project.get('path')}-{branch}.zip?ref_type=heads", project_id)
                )
                new_subdata[project_id] = edit_date

        encoded_subdata = self._generate_subdata(new_subdata)

        return projects_to_index, encoded_subdata

    async def _project_urls(self, subdata: str | None = None, bearer_token: str | None = None) -> tuple[list, str]:
        """Retrieve a structure of files to index."""
        projects = await self._get_projects(bearer_token)
        return self._projects_to_re_index(projects, subdata)

    async def _download_files(self, task_queue: asyncio.Queue, zip_queue: asyncio.Queue) -> None:
        """Download all artifacts from tast_queue and put in zip_queue."""
        async with aiohttp.ClientSession() as session:
            while True:
                task_data = await task_queue.get()
                if task_data is None:
                    break
                url, project_id = task_data
                async with session.get(url) as response:
                    data = await response.read()
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

        pointers_to_projects, new_subdata = await self._project_urls(subdata, bearer_token)
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

    async def execute_get_request(self, url: str, headers: dict | None = None, recursion: int = 0) -> dict:
        """Execute GET request to supplied URL."""
        if headers is None:
            headers = {}

        session = await self.get_session()
        try:
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                response = await resp.json()
        except AssertionError:
            dms_warning(f"Gitlab connector could not make requst to {url}.")
            response = {}
        except (ValueError, aiohttp.InvalidURL) as err:
            dms_error(f"Gitlab URL incorrectly formatted, please export 'CONGITLAB_GITLAB_URL'. (From error: {err})")
        except (aiohttp.ClientResponseError, aiohttp.ClientError):
            if recursion == 0:
                return await self.execute_get_request(url, headers={}, recursion=1)
            dms_warning(f"Unable to access object expected to exist at: {url}. (Got status code {resp.status})")
            response = {}
        return response

    async def execute_head_request(self, url: str, headers: dict | None = None, recursion: int = 0) -> dict:
        """Execute HEAD request to supplied URL."""
        if headers is None:
            headers = {}

        session = await self.get_session()
        try:
            async with session.head(url, headers=headers) as resp:
                resp.raise_for_status()
                response = dict(resp.headers)
        except AssertionError:
            dms_warning(f"Gitlab connector could not make requst to {url}.")
            response = {}
        except (ValueError, aiohttp.InvalidURL) as err:
            dms_error(f"Gitlab URL incorrectly formatted, please export 'CONGITLAB_GITLAB_URL'. (From error: {err})")
        except (aiohttp.ClientResponseError, aiohttp.ClientError):
            if recursion == 0:
                return await self.execute_head_request(url, headers={}, recursion=1)
            dms_warning(f"Unable to access object expected to exist at: {url}. (Got status code {resp.status})")
            response = {}
        return response

    async def execute_post_request(
        self, url: str, headers: dict | None = None, data: dict | None = None, recursion: int = 0
    ) -> dict:
        """Execute POST request to supplied URL."""
        if headers is None:
            headers = {}
        if data is None:
            data = {}

        session = await self.get_session()
        try:
            async with session.post(url, headers=headers, json=data) as resp:
                response = await resp.json()
                resp.raise_for_status()
        except AssertionError:
            dms_warning(f"Gitlab connector could not make requst to {url}.")
            response = {}
        except (ValueError, aiohttp.InvalidURL) as err:
            dms_error(f"Gitlab URL incorrectly formatted, please export 'CONGITLAB_GITLAB_URL'. (From error: {err})")
        except (aiohttp.ClientResponseError, aiohttp.ClientError):
            if recursion == 0:
                return await self.execute_post_request(url, headers={}, data=data, recursion=1)
            dms_warning(f"Unable to access object expected to exist at: {url}. (Got status code {resp.status})")
            response = {}
        return response
