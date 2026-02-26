from setuptools import setup
from pathlib import Path

shared_lib_path = (Path(__file__).parent / "../../shared_functions").resolve().as_uri()

setup(
    install_requires=[
        "fastapi[standard]>=0.128",
        "requests>=2.32",
        f"shared-functions @ {shared_lib_path}",
    ]
)
