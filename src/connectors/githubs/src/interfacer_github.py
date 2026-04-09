"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

GitHub connector following same structure as GitLab connector.
Exposes the same payloads: files + subdata, file_pointers + subdata, and
per-file metadata/content compatible with GitLab's indexer contract.
"""

import base64
import binascii
import io
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urljoin

import requests

from variables import PROJECT, SOURCE_FILE
from unpacker import unpack_values
from dmis_logger import dms_error, dms_info, dms_warning
from initialisation_tools import read_env_variable

HTTP_OK = 200


class GitHub:
    """GitHub connector methods (parity with GitLabs)."""

    session: requests.Session
    api_base: str
    _binary_skip_logs: int
    _binary_skip_log_limit: int

    def __init__(self) -> None:
        """Constructor."""
        self.session = requests.Session()
        raw = read_env_variable("GITHUB_API_URL")
        if not raw:
            raise ValueError("Missing GITHUB_API_URL")
        self.source_system = read_env_variable("GITHUB_SYSTEM_NAME")
        self.api_base = raw.rstrip("/") + "/"
        self._binary_skip_logs = 0
        self._binary_skip_log_limit = 10
        self._set_default_headers()
        self._configure_auth()

    def _set_default_headers(self) -> None:
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    @staticmethod
    def _auth_mode() -> str:
        raw_mode = os.environ.get("GITHUB_AUTH_MODE", "auto").strip().lower()
        if raw_mode in {"legacy", "app", "auto"}:
            return raw_mode
        dms_warning("Unknown GITHUB_AUTH_MODE '%s', using 'auto'.", raw_mode)
        return "auto"

    @staticmethod
    def _incoming_or_legacy_token() -> str | None:
        incoming = os.environ.get("GITHUB_ACCESS_TOKEN")
        if incoming:
            return incoming
        return os.environ.get("GITHUB_TOKEN")

    @staticmethod
    def _app_installation_token() -> str | None:
        # Placeholder for future JWT->installation token exchange.
        return os.environ.get("GITHUB_APP_INSTALLATION_TOKEN")

    def _configure_auth(self) -> None:
        mode = self._auth_mode()
        token: str | None = None

        if mode == "legacy":
            token = self._incoming_or_legacy_token()
        elif mode == "app":
            token = self._app_installation_token()
            if not token:
                dms_warning("GITHUB_AUTH_MODE=app is set but GITHUB_APP_INSTALLATION_TOKEN is missing.")
        else:
            token = self._app_installation_token() or self._incoming_or_legacy_token()

        if not token:
            dms_info("No GitHub auth token configured; connector runs in public (unauthenticated) mode. (rate limits are lower).")
            return

        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _get_repos(self) -> list:
        """Retrieve all repositories the token can access (user or org)."""
        org = os.environ.get("GITHUB_ORG")
        path = f"orgs/{org}/repos" if org else "user/repos"
        out: list = []
        page = 1
        per_page = 100
        while True:
            url = urljoin(
                self.api_base,
                f"{path}?per_page={per_page}&page={page}&sort=pushed",
            )
            chunk = self._execute_request(url)
            if not isinstance(chunk, list) or not chunk:
                break
            out.extend(chunk)
            if len(chunk) < per_page:
                break
            page += 1
        return out

    def get_repo_ids(self) -> dict[str, str]:
        """Map repo full_name -> last push timestamp (ISO), analogous to GitLab project ids."""
        ids: dict[str, str] = {}
        for repo in self._get_repos():
            pushed = repo.get("pushed_at")
            if not pushed:
                continue
            fn = repo.get("full_name")
            if isinstance(fn, str):
                ids[fn] = pushed
        return ids

    def get_repos_as_units(self) -> dict:
        """Repository metadata keyed by html_url (mirrors get_projects_as_units)."""
        content = self._get_repos()
        projects: dict = {}
        for repo in content:
            html_url = repo.get("html_url")
            if not html_url:
                continue
            projects[html_url] = {
                "name": unpack_values(repo, ("name",)),
                "creator": unpack_values(repo, ("owner", "login")),
                "created_date": unpack_values(repo, ("created_at",)),
                "last_edit_date": unpack_values(repo, ("pushed_at",)),
                "type": PROJECT,
            }
        return projects

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

    def _default_branch_for_repo(self, full_name: str) -> str:
        r = self._execute_request(urljoin(self.api_base, f"repos/{full_name}"))
        if isinstance(r, dict):
            b = r.get("default_branch")
            if isinstance(b, str):
                return b
        return "main"

    def _tree_sha_for_branch(self, full_name: str, branch: str) -> str | None:
        ref = self._execute_request(urljoin(self.api_base, f"repos/{full_name}/git/ref/heads/{branch}"))
        if not isinstance(ref, dict):
            return None
        obj = ref.get("object") or {}
        commit_sha = obj.get("sha")
        if not isinstance(commit_sha, str):
            return None
        commit = self._execute_request(urljoin(self.api_base, f"repos/{full_name}/git/commits/{commit_sha}"))
        if not isinstance(commit, dict):
            return None
        tree = commit.get("tree") or {}
        sha = tree.get("sha")
        return sha if isinstance(sha, str) else None

    def get_files_in_repo(self, full_name: str, default_branch: str | None = None) -> list:
        """List content API URLs (pointers) for every blob in the repo tree."""
        branch = default_branch or self._default_branch_for_repo(full_name)
        tree_sha = self._tree_sha_for_branch(full_name, branch)
        if not tree_sha:
            return []
        tree = self._execute_request(urljoin(self.api_base, f"repos/{full_name}/git/trees/{tree_sha}?recursive=1"))
        if not isinstance(tree, dict):
            return []
        files: list = []
        for item in tree.get("tree") or []:
            if item.get("type") != "blob":
                continue
            p = item.get("path")
            if not isinstance(p, str):
                continue
            if self._is_excluded_path(p):
                continue
            files.append(self._make_file_pointer(full_name, p, branch))
        return files

    def _get_clickable_url(self, full_name: str, file_path: str, ref: str) -> str:
        _, _, repo = full_name.partition("/")
        if not repo:
            return ""
        return f"https://github.com/{full_name}/blob/{ref}/{file_path}"

    def _last_commit_date_for_path(self, full_name: str, path: str, ref: str) -> str | None:
        q = quote(path, safe="")
        url = urljoin(
            self.api_base,
            f"repos/{full_name}/commits?path={q}&sha={quote(ref, safe='')}&per_page=1",
        )
        data = self._execute_request(url)
        if isinstance(data, list) and data:
            return unpack_values(data[0], ("commit", "committer", "date"))
        return None

    def get_file(self, pointer: str, include_content: bool = True) -> dict:
        """Fetch one file by pointer URL (GitHub contents API shape normalized to GitLab output)."""
        parsed = self._parse_file_pointer(pointer)
        if not parsed:
            dms_info(f"Could not parse GitHub file pointer: {pointer}")
            return {"metadata": {"unique_pointer": pointer, "type": SOURCE_FILE}}

        full_name, path, ref = parsed
        req_url = self._make_file_pointer(full_name, path, ref)
        file: dict | list = {}
        file = self._execute_request(req_url)
        if isinstance(file, dict) and not include_content:
            file = {k: v for k, v in file.items() if k != "content"}

        if isinstance(file, list):
            file = {}

        name = file.get("name")
        size = file.get("size")
        last_edit = self._last_commit_date_for_path(full_name, path, ref)

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

    def _unpack_zip(self, content: bytes, full_name: str, branch: str) -> list:
        """Unpack GitHub archive zip into the same list shape as GitLabs._unpack_zip."""
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
                try:
                    file_content = zip_file.read(name).decode("utf-8")
                except UnicodeDecodeError as err:
                    file_content = ""
                    if self._binary_skip_logs < self._binary_skip_log_limit:
                        dms_info(f"Skipping binary/non-UTF8 file content: {name}. {err}")
                        self._binary_skip_logs += 1
                        if self._binary_skip_logs == self._binary_skip_log_limit:
                            dms_info("Further binary/non-UTF8 file skip logs are suppressed for this run.")
                enc = self._encode_content_path(intermediate_path)
                unique_pointer = f"{base_pointer_prefix}{enc}?ref={quote(branch, safe='')}"
                files_data.append(
                    {
                        "content": base64.b64encode(file_content.encode("utf-8")).decode("utf-8"),
                        "metadata": {
                            "name": Path(intermediate_path).name,
                            "unique_pointer": unique_pointer,
                            "size": info.file_size,
                            "source_system": self.source_system,
                        },
                    }
                )
        return files_data

    def _files_from_repo_zip(self, full_name: str, branch: str) -> list:
        """Download archive for a repo branch; return file entries or [ ] on failure."""
        owner, _, name = full_name.partition("/")
        zip_url = f"https://codeload.github.com/{owner}/{name}/zip/refs/heads/{branch}"
        resp = requests.get(zip_url, timeout=120)
        if resp.status_code != HTTP_OK:
            dms_info(f"GitHub archive fetch {zip_url} returned {resp.status_code}; skipping repo {full_name}.")
            return []
        return self._unpack_zip(resp.content, full_name, branch)

    def files_to_index(self, subdata: str | None = None) -> dict:
        """Same contract as GitLabs.files_to_index: {"files", "subdata"}."""
        provided_date = self._provided_date(subdata)
        files_data: list = []
        current = self.get_repo_ids()
        repos = self._get_repos()
        latest_update = datetime.min.replace(tzinfo=timezone.utc)

        for repo in repos:
            fn = repo.get("full_name")
            if not isinstance(fn, str):
                continue
            ts = current.get(fn)
            if not isinstance(ts, str):
                continue
            ts_obj = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if ts_obj <= provided_date:
                continue
            latest_update = max(latest_update, ts_obj)
            branch = repo.get("default_branch")
            if not isinstance(branch, str):
                branch = self._default_branch_for_repo(fn)
            files_data.extend(self._files_from_repo_zip(fn, branch))

        generated_subdata = base64.urlsafe_b64encode(latest_update.isoformat().encode()).decode()
        return {"files": files_data, "subdata": generated_subdata}

    def pointers_to_all_files_to_index(self, subdata: str | None) -> dict[str, Any]:
        """Same contract as GitLabs.pointers_to_all_files_to_index: {"subdata", "file_pointers"}."""
        provided_date = self._provided_date(subdata)
        file_pointers: list = []
        repo_ids = self.get_repo_ids()
        latest_update = datetime.min.replace(tzinfo=timezone.utc)
        repos = {r.get("full_name"): r for r in self._get_repos() if r.get("full_name")}

        for full_name, change_time in repo_ids.items():
            if not isinstance(change_time, str):
                continue
            ts_obj = datetime.fromisoformat(change_time.replace("Z", "+00:00"))
            if ts_obj <= provided_date:
                continue
            latest_update = max(latest_update, ts_obj)
            r = repos.get(full_name) or {}
            branch = r.get("default_branch") if isinstance(r, dict) else None
            if not isinstance(branch, str):
                branch = self._default_branch_for_repo(full_name)
            file_pointers.extend(self.get_files_in_repo(full_name, branch))

        generated_subdata = base64.urlsafe_b64encode(latest_update.isoformat().encode()).decode()
        return {"subdata": generated_subdata, "file_pointers": file_pointers}

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

    def _execute_request(self, url: str) -> dict | list:
        try:
            response = self.session.get(url, timeout=120)
            content = response.json()
        except requests.exceptions.JSONDecodeError:
            dms_warning(f"GitHub request to {url} could not be decoded.\nExpected JSON\nGot {response.text[:500]}")
            return {}
        except requests.exceptions.MissingSchema as err:
            dms_error(f"GitHub API URL incorrectly formatted. (From error: {err})")
            return {}
        if response.status_code != HTTP_OK:
            dms_info(f"Request to {url} returned {response.status_code}.")
        return content
