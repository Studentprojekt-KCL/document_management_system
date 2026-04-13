import argparse
import logging
from multiprocessing import Pipe

from search_engine.api.api import API
from search_engine.classifier.classifier import Classifier
from search_engine.search.search_engine import SearchEngine
import signal

class Application:
    search_engine: SearchEngine
    api: API
    classifier: Classifier
    log_level: str

    def __init__(self) -> None:
        logging.basicConfig()

        parser = argparse.ArgumentParser()
        _ = parser.add_argument("--dev", action="store_true")
        args = parser.parse_args()

        if args.dev:
            self.log_level = "debug"
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)
            self.log_level = "info"

        signal.signal(signal.SIGINT, self.signal_handler)
        se_to_api_interface, api_to_se_interface = Pipe()
        self.api: API = API(api_to_se_interface, self.log_level)
        self.search_engine: SearchEngine = SearchEngine(se_to_api_interface, self.log_level)

    def run(self) -> None:
        self.api.start()
        self.search_engine.start()

    def signal_handler(self, signal, frame) -> None:
        self.api.kill()
        self.search_engine.kill()

def run() -> None:
    """Initiate FastAPI using Uvicorn.""" 
    app = Application()
    app.run()
