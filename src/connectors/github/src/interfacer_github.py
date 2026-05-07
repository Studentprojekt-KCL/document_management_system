"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

GitHub connector following same structure as GitLab connector.
Exposes the same payloads: files + subdata, file_pointers + subdata, and
per-file metadata/content compatible with GitLab's indexer contract.
"""

import asyncio
import base64
import binascii
import io
import json
import os
import zipfile
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urljoin

import httpx

from shared_functions.variables import SOURCE_FILE
from shared_functions.unpacker import unpack_values
from shared_functions.file_type_logic import determine_file_type, get_file_resource
from shared_functions.dmis_logger import dms_error, dms_info, dms_warning
from shared_functions.initialisation_tools import read_env_variable

HTTP_OK = 200
REQUEST_TIMEOUT = 120
NUM_WORKERS = 10


class GitHub:
    """GitHub connector."""

    _client: httpx.Client
    api_base: str

    def __init__(self) -> None:
        """Constructor."""
        raw = read_env_variable("CONGITHUB_GITHUB_API_URL")
        if not raw:
            raise ValueError("Missing CONGITHUB_GITHUB_API_URL")
        self.source_system = read_env_variable("CONGITHUB_GITHUB_SYSTEM_NAME")
        self.api_base = raw.rstrip("/") + "/"
        self.org = os.environ.get("CONGITHUB_GITHUB_ORG")
        self._api_version = read_env_variable("CONGITHUB_GITHUB_API_VERSION")
        self._client = httpx.Client(timeout=REQUEST_TIMEOUT)
        file_type_resource = get_file_resource()
        extensions = [extension.get("extension") for extension in file_type_resource]
        descriptions = {extension.get("extension"): extension.get("description") for extension in file_type_resource}
        self.defined_fields = {"content": None, "name": None, "unique_pointer": None, "size": None, "source_system": None} | {
            key: None for key in determine_file_type("", extensions, descriptions)
        }

    def _get_repos(self, token: str | None = None) -> list:
        """Retrieve all repositories the token can access (user or org)."""
        path = f"orgs/{self.org}/repos" if self.org else "user/repos"
        out: list = []
        page = 1
        per_page = 100
        while True:
            url = urljoin(
                self.api_base,
                f"{path}?per_page={per_page}&page={page}&sort=pushed",
            )
            chunk = self._execute_request(url, token)
            if not isinstance(chunk, list) or not chunk:
                break
            out.extend(chunk)
            if len(chunk) < per_page:
                break
            page += 1
        return out

    def get_repo_ids(self, token: str | None = None) -> dict[str, str]:
        """Map repo full_name -> last push timestamp (ISO), analogous to GitLab project ids."""
        ids: dict[str, str] = {}
        for repo in self._get_repos(token):
            pushed = repo.get("pushed_at")
            if not pushed:
                continue
            fn = repo.get("full_name")
            if isinstance(fn, str):
                ids[fn] = pushed
        return ids

    @staticmethod
    def _encode_content_path(path: str) -> str:
        """Encode each path segment for use in GitHub contents API URLs."""
        return "/".join(quote(seg, safe="") for seg in path.split("/") if seg or path == "")

    @staticmethod
    def _is_excluded_path(path: str) -> bool:
        """Optional path filter via env GITHUB_EXCLUDE_PATHS (comma-separated tokens)."""
        raw = os.environ.get("GITHUB_EXCLUDE_PATHS", "")
        if not raw:
            return False
        path_l = path.lower()
        tokens = [t.strip().lower() for t in raw.split(",") if t.strip()]
        if not tokens:
            return False
        return any(token in path_l for token in tokens)

    def _make_file_pointer(self, full_name: str, path: str, ref: str) -> str:
        """Canonical pointer string for a file (used as unique_pointer)."""
        enc = self._encode_content_path(path) if path else ""
        return f"{self.api_base}repos/{full_name}/contents/{enc}?ref={quote(ref, safe='')}"

    def _parse_file_pointer(self, pointer: str) -> tuple[str, str, str] | None:
        """Parse pointer URL into (full_name, path, ref)."""
        p = pointer.strip()
        if "/repos/" not in p or "/contents/" not in p or "?ref=" not in p:
            return None
        try:
            _, rest = p.split("/repos/", 1)
            full_name, after = rest.split("/contents/", 1)
            path_part, _, ref_part = after.partition("?ref=")
            if not full_name or not ref_part:
                return None
            ref_only = ref_part.split("&", 1)[0]
            return full_name, unquote(path_part), unquote(ref_only)
        except ValueError:
            return None

    def _default_branch_for_repo(self, full_name: str, token: str | None = None) -> str:
        r = self._execute_request(urljoin(self.api_base, f"repos/{full_name}"), token)
        if isinstance(r, dict):
            b = r.get("default_branch")
            if isinstance(b, str):
                return b
        return "main"

    def _get_clickable_url(self, full_name: str, file_path: str, ref: str) -> str:
        _, _, repo = full_name.partition("/")
        if not repo:
            return ""
        return f"https://github.com/{full_name}/blob/{ref}/{file_path}"

    def _last_commit_date_for_path(self, full_name: str, path: str, ref: str, token: str | None = None) -> str | None:
        q = quote(path, safe="")
        url = urljoin(
            self.api_base,
            f"repos/{full_name}/commits?path={q}&sha={quote(ref, safe='')}&per_page=1",
        )
        data = self._execute_request(url, token)
        if isinstance(data, list) and data:
            return unpack_values(data[0], ("commit", "committer", "date"))
        return None

    def check_index_needed(self, subdata: str | None, token: str | None = None) -> dict[str, Any]:
        """Check whether any repo has been updated since the provided subdata timestamp."""
        provided_date = self._provided_date(subdata)
        for change_time in self.get_repo_ids(token).values():
            if not isinstance(change_time, str):
                continue
            if datetime.fromisoformat(change_time.replace("Z", "+00:00")) > provided_date:
                return {"index_needed": True}
        return {"index_needed": False}

    def get_file(
        self, pointer: str, include_content: bool = True, include_last_edit_date: bool = True, token: str | None = None
    ) -> dict:
        """Fetch one file by pointer URL (GitHub contents API shape normalized to GitLab output)."""
        parsed = self._parse_file_pointer(pointer)
        if not parsed:
            dms_info(f"Could not parse GitHub file pointer: {pointer}")
            return {"metadata": {"unique_pointer": pointer, "type": SOURCE_FILE}}

        full_name, path, ref = parsed
        req_url = self._make_file_pointer(full_name, path, ref)
        file: dict | list = {}
        file = self._execute_request(req_url, token)
        if isinstance(file, dict) and not include_content:
            file = {k: v for k, v in file.items() if k != "content"}

        if isinstance(file, list):
            file = {}

        name = file.get("name")
        size = file.get("size")
        last_edit = self._last_commit_date_for_path(full_name, path, ref, token) if include_last_edit_date else None

        base_structure: dict[Any, Any] = {
            "metadata": {
                "unique_pointer": pointer,
                "name": name,
                "size": size,
                "last_edit_date": last_edit,
                "type": SOURCE_FILE,
                "source_system": self.source_system,
            }
        }
        if isinstance(path, str):
            base_structure["metadata"]["clickable_url"] = self._get_clickable_url(full_name, path, ref)
        if include_content and isinstance(file.get("content"), str):
            base_structure["content"] = file["content"].replace("\n", "")

        return base_structure

    def get_files(
        self,
        pointers: list[str],
        include_content: bool = False,
        include_last_edit_date: bool = True,
        token: str | None = None,
    ) -> list:
        """Fetch multiple files by pointer, returning a list in GitLab get_files shape."""
        return [self.get_file(pointer, include_content, include_last_edit_date, token) for pointer in pointers]

    def _unpack_zip(self, content: bytes, full_name: str, branch: str) -> list:
        """Unpack GitHub archive zip into the same list shape as GitLab._unpack_zip."""
        base_pointer_prefix = f"{self.api_base}repos/{full_name}/contents/"
        files_data: list = []
        with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
            for name in zip_file.namelist():
                if "/" not in name:
                    continue
                _, intermediate_path = name.split("/", 1)
                if self._is_excluded_path(intermediate_path):
                    continue
                info = zip_file.getinfo(name)
                if info.is_dir():
                    continue
                enc = self._encode_content_path(intermediate_path)
                unique_pointer = f"{base_pointer_prefix}{enc}?ref={quote(branch, safe='')}"
                files_data.append(
                    {
                        "content": base64.b64encode(zip_file.read(name)).decode("utf-8"),
                        "metadata": {
                            "name": Path(intermediate_path).name,
                            "unique_pointer": unique_pointer,
                            "size": info.file_size,
                            "source_system": self.source_system,
                        },
                    }
                )
        return files_data

    async def _download_files(
        self, task_queue: asyncio.Queue, zip_queue: asyncio.Queue, client: httpx.AsyncClient, token: str | None
    ) -> None:
        """Download repo archives from task_queue and put raw bytes into zip_queue."""
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        while True:
            task_data = await task_queue.get()
            if task_data is None:
                task_queue.task_done()
                break
            zip_url, full_name, branch = task_data
            try:
                async with client.stream("GET", zip_url, headers=headers) as response:
                    if response.status_code != HTTP_OK:
                        dms_info(f"GitHub archive fetch {zip_url} returned {response.status_code}; skipping repo {full_name}.")
                    else:
                        data = await response.aread()
                        await zip_queue.put({"data": data, "full_name": full_name, "branch": branch})
            except httpx.HTTPError as err:
                dms_warning(f"GitHub archive download failed for {full_name}: {err}")
            finally:
                task_queue.task_done()

    async def _unzip_files(self, zip_queue: asyncio.Queue, output_queue: asyncio.Queue) -> None:
        """Unzip archives from zip_queue and put unpacked file lists into output_queue."""
        while True:
            item = await zip_queue.get()
            if item is None:
                zip_queue.task_done()
                break
            data = item.get("data")
            full_name = item.get("full_name")
            branch = item.get("branch")
            unpacked = await asyncio.to_thread(self._unpack_zip, data, full_name, branch)
            await output_queue.put(unpacked)
            zip_queue.task_done()

    async def _enqueue_repos(self, repos: list, provided_date: datetime, token: str | None, task_queue: asyncio.Queue) -> datetime:
        """Filter repos by timestamp, enqueue zip download tasks, return the latest push time seen."""
        latest_update = datetime.min.replace(tzinfo=timezone.utc)
        for repo in repos:
            fn = repo.get("full_name")
            if not isinstance(fn, str):
                continue
            ts = repo.get("pushed_at")
            if not isinstance(ts, str):
                continue
            ts_obj = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if ts_obj <= provided_date:
                continue
            latest_update = max(latest_update, ts_obj)
            branch = repo.get("default_branch")
            if not isinstance(branch, str):
                branch = self._default_branch_for_repo(fn, token)
            owner, _, name = fn.partition("/")
            zip_url = urljoin(self.api_base, f"repos/{owner}/{name}/zipball/refs/heads/{branch}")
            await task_queue.put((zip_url, fn, branch))
        return latest_update

    async def stream_files_to_index(self, subdata: str | None = None, token: str | None = None) -> AsyncGenerator[bytes, None]:
        """Streaming equivalent of files_to_index: yields subdata header then one file per chunk."""
        task_queue: asyncio.Queue = asyncio.Queue()
        zip_queue: asyncio.Queue = asyncio.Queue()
        output_queue: asyncio.Queue = asyncio.Queue()

        repos = await asyncio.to_thread(self._get_repos, token)
        latest_update = await self._enqueue_repos(repos, self._provided_date(subdata), token, task_queue)
        generated_subdata = base64.urlsafe_b64encode(latest_update.isoformat().encode()).decode()

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            download_tasks = [
                asyncio.create_task(self._download_files(task_queue, zip_queue, client, token)) for _ in range(NUM_WORKERS)
            ]
            unzip_tasks = [asyncio.create_task(self._unzip_files(zip_queue, output_queue)) for _ in range(NUM_WORKERS)]

            async def producer() -> None:
                await task_queue.join()
                for _ in download_tasks:
                    await task_queue.put(None)
                await zip_queue.join()
                for _ in unzip_tasks:
                    await zip_queue.put(None)
                await output_queue.put(None)

            asyncio.create_task(producer())

            yield json.dumps({"subdata": generated_subdata}).encode("utf-8")

            while True:
                chunk = await output_queue.get()
                if chunk is None:
                    break
                for file in chunk:
                    yield json.dumps(file).encode("utf-8")

    def _files_from_repo_zip(self, full_name: str, branch: str, token: str | None = None) -> list:
        """Download archive for a repo branch; return file entries or [] on failure."""
        owner, _, name = full_name.partition("/")
        zip_url = f"https://codeload.github.com/{owner}/{name}/zip/refs/heads/{branch}"
        resp = self._request(zip_url, token)
        if resp.status_code != HTTP_OK:
            dms_info(f"GitHub archive fetch {zip_url} returned {resp.status_code}; skipping repo {full_name}.")
            return []
        return self._unpack_zip(resp.content, full_name, branch)

    def files_to_index(self, subdata: str | None = None, token: str | None = None) -> dict:
        """Same contract as GitLab.files_to_index: {"files", "subdata"}."""
        provided_date = self._provided_date(subdata)
        files_data: list = []
        repos = self._get_repos(token)
        latest_update = datetime.min.replace(tzinfo=timezone.utc)

        for repo in repos:
            fn = repo.get("full_name")
            if not isinstance(fn, str):
                continue
            ts = repo.get("pushed_at")
            if not isinstance(ts, str):
                continue
            ts_obj = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if ts_obj <= provided_date:
                continue
            latest_update = max(latest_update, ts_obj)
            branch = repo.get("default_branch")
            if not isinstance(branch, str):
                branch = self._default_branch_for_repo(fn, token)
            files_data.extend(self._files_from_repo_zip(fn, branch, token))

        generated_subdata = base64.urlsafe_b64encode(latest_update.isoformat().encode()).decode()
        return {"files": files_data, "subdata": generated_subdata}

    @staticmethod
    def _provided_date(subdata: str | None) -> datetime:
        if subdata is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            subdata_bytes = base64.b64decode(subdata)
        except binascii.Error:
            dms_info("Request with invalid base64 encoding made to GitHub connector: %s", subdata)
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            subdata_str = subdata_bytes.decode("utf-8")
            return datetime.fromisoformat(subdata_str.replace("Z", "+00:00"))
        except (UnicodeDecodeError, ValueError):
            dms_error("GitHub connector could not interpret subdata: %s", subdata)
            return datetime.min.replace(tzinfo=timezone.utc)

    def _request(self, url: str, token: str | None = None) -> httpx.Response:
        """Execute a clean GET request with all headers explicit and no cookie carry-over."""
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self._api_version,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return self._client.get(url, headers=headers, cookies={})

    def _execute_request(self, url: str, token: str | None = None) -> dict | list:
        try:
            response = self._request(url, token)
            content = response.json()
        except json.JSONDecodeError:
            dms_warning(f"GitHub request to {url} could not be decoded.\nExpected JSON\nGot {response.text[:500]}")
            return {}
        except httpx.InvalidURL as err:
            dms_error(f"GitHub API URL incorrectly formatted. (From error: {err})")
            return {}
        if response.status_code != HTTP_OK:
            dms_info(f"Request to {url} returned {response.status_code}.")
        return content
