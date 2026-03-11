"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from pathlib import Path
from setuptools import setup

shared_lib_path = (Path(__file__).parent / "../shared_functions").resolve().as_uri()

setup(
    install_requires=[
        "fastapi[standard] >= 0.128",
        "pydantic-settings",
        "pydantic >= 2.0.0",
        "requests>=2.32",
        "httpx",
        f"shared-functions @ {shared_lib_path}",
    ]
)
