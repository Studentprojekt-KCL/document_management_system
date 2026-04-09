import json

from dmis_logger import dms_error, dms_info
from initialisation_tools import read_env_variable


class ClassifierCache:
    cache_path: str
    cache: dict[str, str]

    def __init__(self) -> None:
        cache_path: str = read_env_variable("SE_API_CLASSIFIER_CACHE_FILE_PATH")

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

    def reset(self) -> None:
        self.cache = {}

    def _write_memory(self):
        with open(self.cache_path, 'w') as f:
            f.write(json.dumps(self.cache))

    def add_classification(self, pointer: str, classification: str) -> None:
        self.cache.update({pointer: classification})
        self._write_memory()

    def remove_classification(self, pointer: str) -> None:
        self.cache.pop(pointer)
        self._write_memory()
        dms_info(f"Removed {pointer} from cache.")

    def fetch_classification(self, pointer: str) -> str | None:
        return self.cache.get(pointer) 
        
