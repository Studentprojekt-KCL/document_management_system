"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from pathlib import Path
from setuptools import setup

shared_lib_path = (Path(__file__).parent / "../../shared_functions").resolve().as_uri()

setup(
    install_requires=[
        "fastapi[standard]>=0.128",
        "requests>=2.32",
        "aiohttp>=3.13",
        f"shared-functions @ {shared_lib_path}",
    ]
)
