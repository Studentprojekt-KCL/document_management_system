"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from pathlib import Path
from setuptools import setup

shared_lib_path = (Path(__file__).parent / "../shared_functions").resolve().as_uri()

setup(
    install_requires=[
        "fastapi[standard] >= 0.128",
        "pydantic-settings",
        "numpy>=2.1.0",
        "torch",
        "transformers >= 4.51.0",
        "safetensors >= 0.4.3",
        "accelerate >= 0.30.0",
        "pydantic >= 2.0.0",
        "sentence-transformers",
        "fastapi[standard]>=0.128",
        "requests>=2.32",
        f"shared-functions @ {shared_lib_path}",
    ]
)
