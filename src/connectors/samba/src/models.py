"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from dataclasses import dataclass


@dataclass
class FileInfo:
    """Object holding file type information"""

    file_extentions: list
    extention_descriptions: dict


@dataclass
class ShareHost:
    """Object holding share and host information."""

    host: str
    port: int
    share: str


@dataclass
class MountOptions:
    """Object holding mount and authentication data."""

    user: str
    password: str
    service_mount: str
    user_mount: str
