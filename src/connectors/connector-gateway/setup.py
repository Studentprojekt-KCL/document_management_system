from pathlib import Path
from setuptools import setup

shared_lib_path = (Path(__file__).parent / "../../shared_functions").resolve().as_uri()

setup(
    install_requires=[
        "fastapi[standard]>=0.128",
        f"shared-functions @ {shared_lib_path}",
        "httpx>=0.28.1"
    ]
)
