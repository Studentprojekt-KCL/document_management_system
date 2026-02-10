from typing import Any

DOWNSTREAM_STRUCTURE = {"data": Any, "search": {"Params": Any, Any: Any}}

UPSTREAM_STRUCTURE = {"title": str, "owner": str, "reference": str | None, "content": str, Any: Any}
