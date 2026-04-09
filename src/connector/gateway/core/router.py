import requests


class FileRouter:
    """HTTP-based router for all connectors."""

    def __init__(self):
        self.connectors = {
            "smb": "http://localhost:8001",
            "gitlab": "http://localhost:8002",
        }

    # =========================
    # POINTER PARSING
    # =========================

    def _parse_pointer(self, pointer: str):
        if "://" not in pointer:
            raise ValueError(f"Invalid pointer: {pointer}")

        source, path = pointer.split("://", 1)

        if source not in self.connectors:
            raise ValueError(f"Unknown source: {source}")

        return source, path

    def _with_source_prefix(self, source: str, pointer: str) -> str:
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

    def get_file(self, pointer: str, include_content=True):
        source, path = self._parse_pointer(pointer)

        r = requests.get(
            f"{self.connectors[source]}/file",
            params={
                "file_pointer": path,
                "include_content": include_content
            },
            timeout=10
        )

        r.raise_for_status()
        return r.json()

    # =========================
    # FILE POINTERS (/files)
    # =========================

    def get_all_pointers(self, subdata: dict | None = None):
        all_pointers = []
        combined_subdata = {}
        connector_errors = []

        subdata = subdata or {}

        for name, base_url in self.connectors.items():
            connector_subdata = subdata.get(name)
            try:
                r = requests.get(
                    f"{base_url}/files",
                    params={"subdata": connector_subdata},
                    timeout=30
                )

                r.raise_for_status()
                result = r.json()

                pointers = result.get("file_pointers", [])

                # Prefix only if connector did not already include source
                prefixed = [self._with_source_prefix(name, p) for p in pointers]

                all_pointers.extend(prefixed)
                combined_subdata[name] = result.get("subdata")
            except Exception as e:
                combined_subdata[name] = connector_subdata
                connector_errors.append({
                    "source": name,
                    "error": str(e)
                })

        response = {
            "file_pointers": all_pointers,
            "subdata": combined_subdata
        }
        if connector_errors:
            response["errors"] = connector_errors
        return response

    # =========================
    # FILES TO INDEX
    # =========================

    def files_to_index(self, subdata: dict | None = None):
        all_files = []
        all_deleted = []
        combined_subdata = {}
        connector_errors = []

        subdata = subdata or {}

        for name, base_url in self.connectors.items():
            connector_subdata = subdata.get(name)
            try:
                r = requests.get(
                    f"{base_url}/files_to_index",
                    params={"subdata": connector_subdata},
                    timeout=180
                )

                r.raise_for_status()
                result = r.json()

                files = result.get("files")
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
            except Exception as e:
                combined_subdata[name] = connector_subdata
                connector_errors.append({
                    "source": name,
                    "error": str(e)
                })

        response = {
            "files": all_files,
            "deleted": all_deleted,
            "subdata": combined_subdata
        }
        if connector_errors:
            response["errors"] = connector_errors
        return response

    # =========================
    # BATCH
    # =========================

    def batch(self, pointers: list[str], include_content=True):
        results = []
        errors = []

        # group by connector (important optimization)
        grouped = {}

        for pointer in pointers:
            try:
                source, path = self._parse_pointer(pointer)
                grouped.setdefault(source, []).append(path)
            except Exception as e:
                errors.append({"pointer": pointer, "error": str(e)})

        # send batch per connector
        for source, paths in grouped.items():
            base_url = self.connectors[source]

            try:
                r = requests.post(
                    f"{base_url}/files/batch",
                    json={
                        "paths": paths,
                        "include_content": include_content
                    },
                    timeout=60
                )

                r.raise_for_status()
                result = r.json()

                results.extend(result.get("files", []))
                errors.extend(result.get("errors", []))

            except Exception as e:
                errors.append({
                    "source": source,
                    "error": str(e)
                })

        return {
            "files": results,
            "errors": errors
        }
