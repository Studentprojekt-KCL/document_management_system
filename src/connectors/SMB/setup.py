"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from pathlib import Path
from setuptools import setup

shared_lib_path = (Path(__file__).parent / "../../shared_functions").resolve().as_uri()

setup(
    install_requires=[
        "fastapi[standard]>=0.128",
        "uvicorn>=0.30",
        "pdfplumber>=0.11",
        "python-docx>=1.0",
        "openpyxl>=3.1",
        f"shared-functions @ {shared_lib_path}",
    ]
)
