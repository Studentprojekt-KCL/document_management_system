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
    for section in path:
        if isinstance(section, str) and isinstance(values, dict):
            values = values.get(section)
        elif isinstance(section, int):
            values = values[section]
        else:
            return None
    return values
