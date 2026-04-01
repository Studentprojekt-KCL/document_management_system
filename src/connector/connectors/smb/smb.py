import os
import json
import base64
import hashlib
import stat
from datetime import datetime
from typing import Any, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None


def smb_error(message: str):
    print(f"ERROR: {message}")


class SMBCollector:

    BASE_PATH = "/mnt/Kernel/projB"
    MAX_FILE_SIZE = 5_000_000
    ALLOWED_EXTENSIONS = (
        ".txt", ".md", ".xml",
        ".pdf", ".docx", ".xlsx"
    )
    SKIP_DIRS = {"drivers", "tools", ".git", ".benchmark_test_perms",".merkle_cache"}
    MAX_WORKERS = 16
    CACHE_DIR = ".merkle_cache"

    def __init__(self) -> None:
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        self._executor: ThreadPoolExecutor | None = None

    # =========================
    # Merkle helpers
    # =========================

    def _project_cache_file(self, project: str) -> str:
        safe_name = "root" if project == "." else project.replace("/", "_")
        return os.path.join(self.CACHE_DIR, f"{safe_name}.json")

    def _load_cache(self, cache_file: str) -> Dict:
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}


    def _save_cache(self, cache: Dict, cache_file: str):
        # säkerställ att katalogen finns
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f)


    def _hash_file(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(262144), b""):
                h.update(chunk)
        return h.hexdigest()

    def _same_meta(self, old_meta: dict, new_meta: dict) -> bool:
        return (
            old_meta.get("size") == new_meta.get("size") and
            old_meta.get("mtime") == new_meta.get("mtime")
        )

    def _scan(self, path: str, old_cache: Dict) -> Tuple[str, Dict]:
        new_cache: Dict[str, Any] = {}

        try:
            entries = os.listdir(path)
        except Exception:
            return "", {}

        h = hashlib.sha256()
        futures = []
        results = {}

        for name in entries:
            full_path = os.path.join(path, name)

            try:
                st = os.stat(full_path)
            except Exception:
                continue

            meta = {"size": st.st_size, "mtime": int(st.st_mtime)}
            mode = st.st_mode

            if stat.S_ISREG(mode):
                old = old_cache.get(full_path)

                if old and self._same_meta(old["meta"], meta):
                    results[full_path] = (name, old["hash"], meta, "file")
                else:
                    future = self._executor.submit(self._hash_file, full_path)
                    futures.append((future, full_path, name, meta))

            elif stat.S_ISDIR(mode):
                if name in self.SKIP_DIRS:
                    continue

                old = old_cache.get(full_path)

                if old and self._same_meta(old["meta"], meta):
                    results[full_path] = (name, old["hash"], meta, "dir")
                else:
                    dir_hash, child_cache = self._scan(full_path, old_cache)
                    new_cache.update(child_cache)
                    results[full_path] = (name, dir_hash, meta, "dir")

        #  non-blocking futures
        future_map = {
            future: (full_path, name, meta)
            for future, full_path, name, meta in futures
        }

        from concurrent.futures import TimeoutError

        for future in as_completed(future_map, timeout=10):
            full_path, name, meta = future_map[future]
            try:
                file_hash = future.result(timeout=2)
                results[full_path] = (name, file_hash, meta, "file")
            except TimeoutError:
                smb_error(f"Hash timed out for {full_path}")
        #  no sorting
        for full_path, (name, item_hash, meta, item_type) in results.items():
            h.update(name.encode())
            h.update(item_hash.encode())

            new_cache[full_path] = {
                "hash": item_hash,
                "meta": meta,
                "type": item_type
            }

        new_cache[path] = {
            "hash": h.hexdigest(),
            "meta": {"size": 0, "mtime": 0},
            "type": "dir"
        }

        return h.hexdigest(), new_cache

    def _diff(self, old_cache: Dict, new_cache: Dict):
        added, removed, modified = [], [], []

        for path in new_cache:
            if path not in old_cache:
                added.append((path, new_cache[path]["type"]))
            elif old_cache[path]["hash"] != new_cache[path]["hash"]:
                modified.append((path, new_cache[path]["type"]))

        for path in old_cache:
            if path not in new_cache:
                removed.append((path, old_cache[path]["type"]))

        return added, removed, modified

    def _run_merkle_for_project(self, project: str):
        path = self.BASE_PATH if project == "." else os.path.join(self.BASE_PATH, project)
        cache_file = self._project_cache_file(project)

        old_cache = self._load_cache(cache_file)
        root_hash, new_cache = self._scan(path, old_cache)

        added, removed, modified = self._diff(old_cache, new_cache)
        self._save_cache(new_cache, cache_file)

        return {
            "root_hash": root_hash,
            "added": added,
            "removed": removed,
            "modified": modified,
        }

    # =========================
    # Projects
    # =========================

    def _get_projects(self) -> list[dict]:
        try:
            entries = os.listdir(self.BASE_PATH)
        except Exception:
            return []

        projects = []
        for d in entries:
            if d.startswith("."):
                continue
            full_path = os.path.join(self.BASE_PATH, d)
            if os.path.isdir(full_path):
                stat_ = os.stat(full_path)
                projects.append({
                    "name": d,
                    "path": full_path,
                    "size": stat_.st_size,
                    "last_modified": datetime.fromtimestamp(stat_.st_mtime).isoformat(),
                })
        return projects

    def get_project_ids(self) -> dict[str, str]:
        ids = {}
        for project in self._get_projects():
            result = self._run_merkle_for_project(project["name"])
            ids[project["name"]] = result["root_hash"]
        return ids

    def get_projects_as_units(self) -> dict:
        projects = {}
        for project in self._get_projects():
            path = project["path"]
            projects[path] = {
                "name": project["name"],
                "last_edit_date": os.path.getmtime(path),
                "type": "project",
            }
        return projects

    # =========================
    # Parsing
    # =========================

    def parse_file(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except:
            return ""

    # =========================
    # Processing
    # =========================

    def _process_file(self, file_path: str) -> dict:
        st = os.stat(file_path)

        try:
            content = self.parse_file(file_path)
            encoded = base64.b64encode(content.encode()).decode()
        except:
            encoded = ""

        return {
            "metadata": {
                "unique_pointer": f"smb://{file_path}",
                "name": os.path.basename(file_path),
                "size": st.st_size,
                "last_edit_date": st.st_mtime,
                "type": "source_file",
            },
            "content": encoded
        }

    # =========================
    # Indexing
    # =========================

    def files_to_index(self, subdata=None):
        files_data = []
        deleted_files = []

        subdata_dict = {}
        if subdata:
            try:
                subdata_dict = json.loads(base64.b64decode(subdata))
            except:
                pass

        current_subdata = {}

        self._executor = ThreadPoolExecutor(max_workers=self.MAX_WORKERS)

        try:
            for project in self._get_projects():
                result = self._run_merkle_for_project(project["name"])
                current_subdata[project["name"]] = result["root_hash"]

                if result["root_hash"] == subdata_dict.get(project["name"]):
                    continue

                changed_files = [
                    p for p, t in (result["added"] + result["modified"])
                    if t == "file" and self._is_valid_file(p)
                ]

                deleted_files.extend([p for p, _ in result["removed"]])

                futures = [self._executor.submit(self._process_file, f) for f in changed_files]

                for future in as_completed(futures):
                    try:
                        files_data.append(future.result())
                    except Exception as e:
                        smb_error(f"Processing failed: {e}")

        finally:
            self._executor.shutdown()
            self._executor = None

        print("PROJECTS:", self._get_projects())
        print("SUBDATA:", subdata_dict)
        print("CURRENT:", current_subdata)

        return {
            "files": files_data,
            "deleted": deleted_files,
            "subdata": base64.b64encode(json.dumps(current_subdata).encode()).decode()
        }

    def get_files_in_project(self, project: str) -> list[str]:
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
    
    def get_file(self, path: str, include_content: bool = True) -> dict:
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} not found")

        result = self._process_file(path)

        if not include_content:
            result.pop("content", None)

        return result

    def pointers_to_all_files_to_index(self, subdata=None):
        file_pointers = []
        deleted_files = []
        current_subdata = {}

        self._executor = ThreadPoolExecutor(max_workers=self.MAX_WORKERS)

        try:
            for project in self._get_projects():
                result = self._run_merkle_for_project(project["name"])
                current_subdata[project["name"]] = result["root_hash"]

                file_pointers.extend([
                    p for p, t in (result["added"] + result["modified"])
                    if t == "file" and self._is_valid_file(p)
                ])

                deleted_files.extend([p for p, _ in result["removed"]])

        finally:
            self._executor.shutdown()
            self._executor = None

        return {
            "file_pointers": file_pointers,
            "deleted": deleted_files,
            "subdata": base64.b64encode(json.dumps(current_subdata).encode()).decode()
        }

    def _is_valid_file(self, path):
        try:
            return path.lower().endswith(self.ALLOWED_EXTENSIONS) and os.path.getsize(path) <= self.MAX_FILE_SIZE
        except:
            return False
        
