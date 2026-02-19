"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from collections.abc import Iterable
from typing import Any


def unpack_values(values: Iterable, path: tuple) -> Any:
    """For a defined path through a recursively defined iterable object, retrieve the defined value.
        If no value exists, return None.

    Args:
    ----
        values: Recursively defined iterable object to unpack.
        path: Path through recursive object.
    """
    if not isinstance(values, Iterable):
        return None
    value: Any = values
    for section in path:
        if isinstance(section, str) and isinstance(value, dict):
            value = value.get(section)
        elif isinstance(section, int):
            value = value[section]
        else:
            return None
    return value
