from typing import Tuple, Dict, Any

from connectors.smb.smb import SMBCollector

# Lägg till senare när du har GitLab
# from connectors.gitlab.gitlab import GitLabs


class FileRouter:
    """Unified router for all file systems."""

    def __init__(self):
        self.connectors = {
            "smb": SMBCollector(),
            # "gitlab": GitLabs(),
        }

    # =========================
    # POINTER PARSING
    # =========================

    def _parse_pointer(self, pointer: str) -> Tuple[str, str]:
        if "://" not in pointer:
            raise ValueError(f"Invalid pointer format: {pointer}")

        source, path = pointer.split("://", 1)

        if source not in self.connectors:
            raise ValueError(f"Unsupported source: {source}")

        return source, path

    # =========================
    # SINGLE FILE
    # =========================

    def get_file(self, pointer: str, include_content: bool = True) -> Dict[str, Any]:
        source, real_path = self._parse_pointer(pointer)

        connector = self.connectors[source]

        return connector.get_file(real_path, include_content)

    # =========================
    # BATCH
    # =========================

    def batch(self, pointers: list[str], include_content: bool = True) -> dict:
        results = []
        errors = []

        for pointer in pointers:
            try:
                data = self.get_file(pointer, include_content)
                results.append(data)

            except Exception as e:
                errors.append({
                    "pointer": pointer,
                    "error": str(e)
                })

        return {
            "files": results,
            "errors": errors
        }

    # =========================
    # POINTERS (ALL SYSTEMS)
    # =========================

    def get_all_pointers(self, subdata: dict | None = None) -> dict:
        all_pointers = []
        combined_subdata = {}

        for name, connector in self.connectors.items():
            result = connector.pointers_to_all_files_to_index(subdata)

            prefixed = [
                f"{name}://{p}"
                for p in result.get("file_pointers", [])
            ]

            all_pointers.extend(prefixed)
            combined_subdata[name] = result.get("subdata")

        return {
            "file_pointers": all_pointers,
            "subdata": combined_subdata
        }

    # =========================
    # FILES TO INDEX
    # =========================

    def files_to_index(self, subdata: dict | None = None) -> dict:
        all_files = []
        combined_subdata = {}

        for name, connector in self.connectors.items():
            result = connector.files_to_index(subdata)

            for f in result.get("files", []):
                # prefix pointer
                f["metadata"]["unique_pointer"] = f"{name}://{f['metadata']['unique_pointer']}"
                all_files.append(f)

            combined_subdata[name] = result.get("subdata")

        return {
            "files": all_files,
            "subdata": combined_subdata
        }
