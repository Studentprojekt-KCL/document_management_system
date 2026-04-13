import json
from threading import Event, Thread

from dmis_logger import dms_info, dms_warning


class Writer(Thread):
    WRITE_INTERVALS: int = 20
    cache_file: str
    queue: list[dict[str, str] | None]
    close_event: Event

    def __init__(self, cache_file: str) -> None:
        super().__init__()
        self.queue = []
        self.cache_file = cache_file
        self.close_event = Event()

    def add(self, item: dict[str, str]) -> None:
        self.queue.append(item)

    def close(self) -> None:
        dms_info("Closing writer thread.")
        self.queue.append(None)
        self.close_event.set()

    def run(self) -> None:
        dms_info("Launching writer thread.")
        while True:
            self.close_event.wait(timeout=Writer.WRITE_INTERVALS)
            dms_info("Adding new classifications.")
            try:
                with open(self.cache_file, "a", encoding="utf=8") as f:
                    while self.queue:
                        classification: dict[str, str] | None = self.queue.pop()
                        if classification is None:
                            break
                        f.write(json.dumps(classification))
            except OSError:
                dms_warning(f"Failed to open (write): {self.cache_file}.")
