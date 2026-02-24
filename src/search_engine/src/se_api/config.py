from os import environ
from logger import dms_error
import argparse

class APIConfiguration:
    port: int
    host: str
    log_level: str | None = None

    def __init__(self): 
        try:
            self.load_port()
            self.load_host()
            self.load_log_level()
        except RuntimeError as e:
            dms_error(repr(e))
            self.port = 0
            self.host = ""
            self.log_level = None

    def load_port(self):
        temp: str | None = environ.get("SE_API_PORT", None)
        port: int = 0

        if temp is None:
            port = 8080
        else:
            try:
                port = int(temp) 
            except ValueError:
                raise RuntimeError(f"Expected SE_API_PORT to be an integer, but got {temp} ({type(temp)})")

        if port < 0 or port > 65536:
            raise RuntimeError(f"SE_API_PORT expected value to be between 0 and 65536, but is {port}")

        self.port = port

    def load_host(self):
        self.host = "0.0.0.0"

    def load_log_level(self):
        parser = argparse.ArgumentParser()
        _ = parser.add_argument("--dev", action="store_true")
        args = parser.parse_args()

        if args.dev:
            self.log_level = "debug"


