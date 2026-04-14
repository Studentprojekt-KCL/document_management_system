"""router.py - HTTP-based router for all connectors."""

from typing import List, Dict, Any
import requests
from requests.exceptions import RequestException


class FileRouter:
    """HTTP-based router for all connectors."""

    def __init__(self) -> None:
        self.connectors: Dict[str, str] = {
            "smb": "http://localhost:8001",
            "gitlab": "http://localhost:8002",
        }

    # =========================
    # POINTER PARSING
    # =========================

    def _parse_pointer(self, pointer: str) -> tuple[str, str]:
        """Parse a pointer into (source, path). E.g. smb://path/to/file.txt -> ("smb", "path/to/file.txt")"""
        if "://" not in pointer:
            raise ValueError(f"Invalid pointer: {pointer}")

        source, path = pointer.split("://", 1)

        if source not in self.connectors:
            raise ValueError(f"Unknown source: {source}")

        return source, path

    def _with_source_prefix(self, source: str, pointer: str) -> str:
        """Ensure the pointer has the source prefix. E.g. "path/to/file.txt" -> "smb://path/to/file.txt" if source is smb."""
        if not isinstance(pointer, str):
            pointer = str(pointer)
        if "://" in pointer:
            existing_source = pointer.split("://", 1)[0]
            if existing_source in self.connectors:
                return pointer
        return f"{source}://{pointer}"

    # =========================
    # SINGLE FILE
    # =========================

    def get_file(self, pointer: str, include_content: bool = True) -> Dict[str, Any]:
        """Get a single file by pointer. E.g. smb://path/to/file.txt"""
        source, path = self._parse_pointer(pointer)

        r = requests.get(
            f"{self.connectors[source]}/file", params={"file_pointer": path, "include_content": str(include_content)}, timeout=10
        )

        r.raise_for_status()
        return r.json()

    # =========================
    # FILE POINTERS (/files)
    # =========================

    def get_all_pointers(self, subdata: dict | None = None) -> Dict[str, Any]:
        """Get all file pointers from all connectors, with optional subdata for each connector."""
        all_pointers: List[str] = []
        combined_subdata: Dict[str, Any] = {}
        connector_errors: List[Dict[str, Any]] = []

        subdata = subdata or {}

        for name, base_url in self.connectors.items():
            connector_subdata = subdata.get(name)

            try:
                r = requests.get(
                    f"{base_url}/files",
                    params={"subdata": connector_subdata},
                    timeout=30,
                )
                r.raise_for_status()

                result = r.json()
                if not isinstance(result, dict):
                    continue

                # --- FIX: säker extraktion av pointers ---
                raw_pointers = result.get("file_pointers")

                pointers: List[str] = []
                if isinstance(raw_pointers, list):
                    for item in raw_pointers:
                        if isinstance(item, str):
                            pointers.append(item)

                # --- FIX: explicit typning ---
                prefixed: List[str] = []
                for p in pointers:
                    prefixed.append(self._with_source_prefix(name, p))

                all_pointers.extend(prefixed)

                combined_subdata[name] = result.get("subdata")

            except RequestException as e:
                combined_subdata[name] = connector_subdata
                connector_errors.append({"source": name, "error": str(e)})

        response: Dict[str, Any] = {
            "file_pointers": all_pointers,
            "subdata": combined_subdata,
        }

        if connector_errors:
            response["errors"] = connector_errors

        return response

    # =========================
    # FILES TO INDEX
    # =========================

    def files_to_index(self, subdata: dict | None = None) -> Dict[str, Any]:
        """Get files to index from all connectors, with optional subdata for
        each connector. Returns combined list of files and deleted pointers."""
        all_files: List[Dict[str, Any]] = []
        all_deleted: List[str] = []
        combined_subdata: Dict[str, Any] = {}
        connector_errors: List[Dict[str, Any]] = []

        subdata = subdata or {}

        for name, base_url in self.connectors.items():
            connector_subdata = subdata.get(name)
            try:
                r = requests.get(f"{base_url}/files_to_index", params={"subdata": connector_subdata}, timeout=180)

                r.raise_for_status()
                result: Dict[str, Any] = r.json()

                files: List[Dict[str, Any]] | None = result.get("files")
                deleted = result.get("deleted", [])

                # GitLab connector may return a file_url containing the payload.
                if files is None and result.get("file_url"):
                    file_resp = requests.get(result["file_url"], timeout=120)
                    file_resp.raise_for_status()
                    external_payload = file_resp.json()
                    files = external_payload.get("files", [])
                    deleted = external_payload.get("deleted", [])

                for f in files or []:
                    all_files.append(f)
                all_deleted.extend([self._with_source_prefix(name, p) for p in deleted])

                combined_subdata[name] = result.get("subdata")
            except RequestException as e:
                combined_subdata[name] = connector_subdata
                connector_errors.append({"source": name, "error": str(e)})

        response = {"files": all_files, "deleted": all_deleted, "subdata": combined_subdata}
        if connector_errors:
            response["errors"] = connector_errors
        return response

    # =========================
    # BATCH
    # =========================

    def batch(self, pointers: List[str], include_content: bool = True) -> Dict[str, Any]:
        """Get multiple files by pointers. E.g. ["smb://path/to/file.txt", "gitlab://repo/path/to/file.md"]"""
        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        # group by connector
        grouped: Dict[str, List[str]] = {}

        for pointer in pointers:
            try:
                source, path = self._parse_pointer(pointer)
                grouped.setdefault(source, []).append(path)
            except ValueError as e:
                errors.append({"pointer": pointer, "error": str(e)})

        # send batch per connector
        for source, paths in grouped.items():
            base_url = self.connectors[source]

            try:
                r = requests.post(f"{base_url}/files/batch", json={"paths": paths, "include_content": include_content}, timeout=60)

                r.raise_for_status()
                result: Dict[str, Any] = r.json()

                results.extend(result.get("files", []))
                errors.extend(result.get("errors", []))

            except RequestException as e:
                errors.append({"source": source, "error": str(e)})

        return {"files": results, "errors": errors}
