"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from pathlib import Path
from setuptools import setup

shared_lib_path = (Path(__file__).parent / "../shared_functions").resolve().as_uri()

setup(
    install_requires=[
        "fastapi[standard]>=0.128",
        "tantivy>=0.25",
        "httpx>=0.28",
        "markitdown[pptx, docx, xlsx, xls, pdf]>=0.1.5",
        f"shared-functions @ {shared_lib_path}",
    ]
)
