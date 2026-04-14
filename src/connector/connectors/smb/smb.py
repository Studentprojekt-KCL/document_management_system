"""pass the test"""

import os
import json
import base64
import hashlib
import stat
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Tuple, List


def smb_error(message: str) -> None:
    """Print a standardized SMB error message."""
    logging.error("SMB error: %s", message)


def _env_int(name: str, default: int) -> int:
    """Read an integer from environment with fallback."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_csv_set(name: str, default: set[str]) -> set[str]:
    """Read a comma-separated environment value into a set."""
    value = os.environ.get(name)
    if value is None:
        return default
    parts = [v.strip() for v in value.split(",")]
    cleaned = {v for v in parts if v}
    return cleaned or default


def _env_csv_tuple(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    """Read comma-separated extensions from environment into a tuple."""
    value = os.environ.get(name)
    if value is None:
        return default
    parts = [v.strip().lower() for v in value.split(",")]
    cleaned = tuple(v if v.startswith(".") else f".{v}" for v in parts if v)
    return cleaned or default


class SMBCollector:
    """Collector for SMB file system, building a Merkle tree to track changes."""

    BASE_PATH = os.environ.get("SMB_BASE_PATH", "/mnt/Kernel/projB")
    MAX_FILE_SIZE = _env_int("SMB_MAX_FILE_SIZE", 5_000_000)
    ALLOWED_EXTENSIONS = _env_csv_tuple("SMB_ALLOWED_EXTENSIONS", (".txt", ".md", ".xml", ".pdf", ".docx", ".xlsx"))
    SKIP_DIRS = _env_csv_set("SMB_SKIP_DIRS", {"drivers", "tools", ".git", ".benchmark_test_perms", ".merkle_cache"})
    MAX_WORKERS = _env_int("SMB_MAX_WORKERS", 16)
    CACHE_DIR = os.environ.get("SMB_CACHE_DIR", ".merkle_cache")

    def __init__(self) -> None:
        """Initialize collector state and ensure cache directory exists."""
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        self._executor: ThreadPoolExecutor | None = None

    # =========================
    # Merkle helpers
    # =========================

    def _load_cache(self, cache_file: str) -> Dict[str, Any]:
        """Load the Merkle cache tree from disk."""
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return {}
        return {}

    def _save_cache(self, cache: Dict[str, Any], cache_file: str) -> None:
        """Persist the Merkle cache tree to disk."""
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f)

    def _hash_file(self, file_path: str) -> str:
        """Calculate SHA-256 for a file using chunked reads."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(262144), b""):
                h.update(chunk)
        return h.hexdigest()

    def _cache_file(self) -> str:
        """Return the cache file path for this collector."""
        return os.path.join(self.CACHE_DIR, "cache.json")

    def _same_meta(self, old_meta: Dict[str, Any], new_meta: Dict[str, Any]) -> bool:
        """Check whether metadata indicates unchanged file content."""
        old_mtime = old_meta.get("mtime_ns", old_meta.get("mtime"))
        new_mtime = new_meta.get("mtime_ns", new_meta.get("mtime"))
        return old_meta.get("size") == new_meta.get("size") and old_mtime == new_mtime

    def _build_global_root(self, project_hashes: dict[str, str]) -> str:
        """Build deterministic global hash from project root hashes."""
        h = hashlib.sha256()

        for name in sorted(project_hashes):
            h.update(name.encode())
            h.update(project_hashes[name].encode())

        return h.hexdigest()

    def _scan_tree(self, path: str, old_node: Dict[str, Any] | None) -> Dict[str, Any]:
        """Recursively build a Merkle tree and reuse unchanged nodes."""
        try:
            st = os.stat(path)
        except OSError:
            return {}

        meta = {"size": st.st_size, "mtime_ns": st.st_mtime_ns}

        # =========================
        # FILE
        # =========================
        if stat.S_ISREG(st.st_mode):
            if old_node and self._same_meta(old_node.get("meta", {}), meta):
                return old_node  # reuse hash

            return {"type": "file", "hash": self._hash_file(path), "meta": meta}

        # =========================
        # DIRECTORY
        # =========================
        if not stat.S_ISDIR(st.st_mode):
            return {}

        children = {}
        results = {}
        futures = {}

        try:
            entries = os.listdir(path)
        except OSError:
            return {}

        for name in entries:
            if name in self.SKIP_DIRS:
                continue

            full_path = os.path.join(path, name)
            old_child = (old_node or {}).get("children", {}).get(name)

            try:
                st_child = os.stat(full_path)
            except OSError:
                continue

            meta_child = {"size": st_child.st_size, "mtime_ns": st_child.st_mtime_ns}

            # =========================
            # FILE CHILD
            # =========================
            if stat.S_ISREG(st_child.st_mode):

                if old_child and self._same_meta(old_child.get("meta", {}), meta_child):
                    results[name] = old_child  # reuse
                else:
                    assert self._executor is not None
                    futures[self._executor.submit(self._hash_file, full_path)] = (name, meta_child)

            # =========================
            # DIR CHILD
            # =========================
            elif stat.S_ISDIR(st_child.st_mode):
                node = self._scan_tree(full_path, old_child)
                if node:
                    results[name] = node

        # =========================
        # RESOLVE FILE HASHES
        # =========================
        for future in as_completed(futures):
            name, meta_child = futures[future]
            try:
                file_hash = future.result()
                results[name] = {"type": "file", "hash": file_hash, "meta": meta_child}
            except OSError as exc:
                smb_error(f"Hash failed for {name}: {exc}")

        # =========================
        # BUILD DIR HASH (deterministic)
        # =========================
        h = hashlib.sha256()

        for name in sorted(results):
            node = results[name]
            h.update(name.encode())
            h.update(node["hash"].encode())
            children[name] = node

        return {"type": "dir", "hash": h.hexdigest(), "meta": meta, "children": children}

    def _diff_tree(
        self, old: Dict[str, Any], new: Dict[str, Any], path: str = ""
    ) -> Tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
        """Return added, removed and modified nodes between two trees."""
        added, removed, modified = [], [], []

        old_children = old.get("children", {}) if old else {}
        new_children = new.get("children", {}) if new else {}

        # added + modified
        for name, new_node in new_children.items():
            full_path = os.path.join(path, name)

            if name not in old_children:
                added.append((full_path, new_node["type"]))
            else:
                old_node = old_children[name]

                if old_node["hash"] != new_node["hash"]:
                    if new_node["type"] == "dir":
                        a, r, m = self._diff_tree(old_node, new_node, full_path)
                        added += a
                        removed += r
                        modified += m
                    else:
                        modified.append((full_path, "file"))

        # removed
        for name, old_node in old_children.items():
            if name not in new_children:
                removed.append((os.path.join(path, name), old_node["type"]))

        return added, removed, modified

    # =========================
    # Projects
    # =========================

    def _get_projects(self) -> list[Dict[str, Any]]:
        """List top-level project directories from SMB base path."""
        try:
            entries = os.listdir(self.BASE_PATH)
        except OSError:
            return []

        projects: list[Dict[str, Any]] = []
        for d in entries:
            if d.startswith("."):
                continue
            full_path = os.path.join(self.BASE_PATH, d)
            if os.path.isdir(full_path):
                stat_ = os.stat(full_path)
                projects.append(
                    {
                        "name": d,
                        "path": full_path,
                        "size": stat_.st_size,
                        "last_modified": datetime.fromtimestamp(stat_.st_mtime).isoformat(),
                    }
                )
        return projects

    # =========================
    # Parsing
    # =========================

    def parse_file(self, file_path: str) -> str:
        """Read file content as UTF-8 text with tolerant decoding."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except OSError:
            return ""

    # =========================
    # Processing
    # =========================

    def _process_file(self, file_path: str) -> Dict[str, Any]:
        """Build normalized index payload for one file."""
        st = os.stat(file_path)

        try:
            content = self.parse_file(file_path)
            encoded = base64.b64encode(content.encode()).decode()
        except (OSError, UnicodeEncodeError):
            encoded = ""

        return {
            "metadata": {
                "unique_pointer": f"smb://{file_path}",
                "name": os.path.basename(file_path),
                "size": st.st_size,
                "last_edit_date": st.st_mtime,
                "type": "source_file",
            },
            "content": encoded,
        }

    # =========================
    # Indexing
    # =========================

    def files_to_index(self, subdata: str | None = None) -> Dict[str, Any]:
        """Return changed file payloads, deletions and next subdata token."""
        files_data: list[Dict[str, Any]] = []
        deleted_files: list[str] = []

        old_hash: str | None = None
        if subdata:
            try:
                old_hash = base64.b64decode(subdata).decode()
            except (ValueError, UnicodeDecodeError):
                pass

        self._executor = ThreadPoolExecutor(max_workers=self.MAX_WORKERS)

        try:
            merkle_result = self._run_merkle()
            current_hash: str = merkle_result["root_hash"] or ""

            # FAST SKIP
            if current_hash == old_hash:
                return {
                    "files": [],
                    "deleted": [],
                    "subdata": base64.b64encode(current_hash.encode()).decode(),
                    "root_hash": current_hash,
                }

            changed_files = [
                p for p, t in (merkle_result["added"] + merkle_result["modified"]) if t == "file" and self._is_valid_file(p)
            ]

            deleted_files = [p for p, _ in merkle_result["removed"]]

            futures = [self._executor.submit(self._process_file, f) for f in changed_files]

            for future in as_completed(futures):
                try:
                    files_data.append(future.result())
                except OSError as exc:
                    smb_error(f"Processing failed: {exc}")

        finally:
            if self._executor:
                self._executor.shutdown()
                self._executor = None

        return {
            "files": files_data,
            "deleted": deleted_files,
            "subdata": base64.b64encode(current_hash.encode()).decode(),
            "root_hash": current_hash,
        }

    def _run_merkle(self) -> Dict[str, Any]:
        """Load cache, scan tree, diff changes and persist new cache."""
        cache_file = self._cache_file()

        old_cache = self._load_cache(cache_file)

        new_tree = self._scan_tree(self.BASE_PATH, old_cache)

        added, removed, modified = self._diff_tree(old_cache, new_tree, self.BASE_PATH)

        self._save_cache(new_tree, cache_file)
        return {"root_hash": new_tree.get("hash"), "added": added, "removed": removed, "modified": modified}

    def get_files_in_project(self, project: str) -> list[str]:
        """Return all file paths for a project, excluding skipped dirs."""
        if project == ".":
            project_path = self.BASE_PATH
        else:
            project_path = os.path.join(self.BASE_PATH, project)

        files: list[str] = []

        for root, dirs, filenames in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]

            for filename in filenames:
                files.append(os.path.join(root, filename))

        return files

    def get_file(self, path: str, include_content: bool = True) -> Dict[str, Any]:
        """Return a single file payload, optionally without content."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} not found")

        file_result = self._process_file(path)

        if not include_content:
            file_result.pop("content", None)

        return file_result

    def pointers_to_all_files_to_index(self, subdata: str | None = None) -> Dict[str, Any]:
        """Return pointers for changed files plus deleted files and subdata."""
        file_pointers: List[str] = []
        deleted_files: List[str] = []

        old_hash: str | None = None
        if subdata:
            try:
                old_hash = base64.b64decode(subdata).decode()
            except (ValueError, UnicodeDecodeError):
                pass

        self._executor = ThreadPoolExecutor(max_workers=self.MAX_WORKERS)

        try:
            merkle_result = self._run_merkle()
            current_hash = merkle_result["root_hash"] or ""

            # FAST SKIP
            if current_hash == old_hash:
                return {"file_pointers": [], "deleted": [], "subdata": base64.b64encode(current_hash.encode()).decode()}

            file_pointers = [
                p for p, t in (merkle_result["added"] + merkle_result["modified"]) if t == "file" and self._is_valid_file(p)
            ]

            deleted_files = [p for p, _ in merkle_result["removed"]]

        finally:
            if self._executor:
                self._executor.shutdown()
                self._executor = None

        return {
            "file_pointers": file_pointers,
            "deleted": deleted_files,
            "subdata": base64.b64encode(current_hash.encode()).decode(),
        }

    def _is_valid_file(self, path: str) -> bool:
        """Check extension and max-size rules for indexable files."""
        try:
            return path.lower().endswith(self.ALLOWED_EXTENSIONS) and os.path.getsize(path) <= self.MAX_FILE_SIZE
        except OSError:
            return False


if __name__ == "__main__":
    collector = SMBCollector()
    start = datetime.now()
    main_result = collector.files_to_index()
    end = datetime.now()
    logging.info("SMB collector run completed in %s", end - start)
    logging.info(
        "files=%s deleted=%s subdata_len=%s",
        len(main_result.get("files", [])),
        len(main_result.get("deleted", [])),
        len(main_result.get("subdata", "")),
    )
