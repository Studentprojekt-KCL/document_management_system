"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from pathlib import Path
from setuptools import setup

shared_lib_path = (Path(__file__).parent / "../shared_functions").resolve().as_uri()

setup(
    install_requires=[
        "fastapi[standard] >= 0.128",
        "uvicorn",
        "pydantic >= 2.0.0",
        "requests>=2.32",
        "httpx",
        "markdown-pdf>=1.13.1",
        "markitdown[docx,pptx,xlsx,pdf]>=0.1",
        "tokenizers>=0.20",
        f"shared-functions @ {shared_lib_path}",
    ]
)
