import json
from os import environ
from base64 import b64decode, b64encode

from dmis_logger import dms_error, dms_info


class ClassifierCache:
    cache_path: str
    cache: dict[str, str]

    def __init__(self) -> None:
        cache_path: str | None = environ.get("SE_API_CLASSIFIER_CACHE_FILE_PATH")
        if cache_path is None:
            dms_error("SE_API_CLASSIFIER_CACHE_FILE_PATH is not defined.")
            return

        try:
            with open(cache_path, 'r') as f:
                cache: dict = json.loads(f.read())
                self.cache = cache
        except OSError:
            dms_error(f"File {cache_path} doesnt exist.")
            return
        except json.JSONDecodeError:
            self.cache = {}
         
        self.cache_path = cache_path

    def _write_memory(self):
        with open(self.cache_path, 'w') as f:
            f.write(json.dumps(self.cache))

    def _encode(self, pointer: str) -> str:
        return b64encode(pointer.encode("utf-8")).decode("utf-8")

    def _decode(self, key: str) -> str:
        return b64decode(key.encode("utf-8")).decode("utf-8")

    def add_classification(self, pointer: str, classification: str) -> None:
        self.cache.update({self._encode(pointer): classification})
        self._write_memory()

    def remove_classification(self, pointer: str) -> None:
        self.cache.pop(self._encode(pointer))
        self._write_memory()

    def fetch_classification(self, pointer: str) -> str | None:
        classification: str | None = self.cache.get(self._encode(pointer)) 
        if classification is not None:
            dms_info(f"Grabbed cached: {pointer}")
        return classification
        
