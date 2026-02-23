"""Search engine API unit tests."""

from datetime import datetime
from fastapi.responses import JSONResponse
from se_api.api import API
from se_api.models import Query, Metadata, File
import pytest


@pytest.fixture
def api_obj() -> API:
    """Create API object."""
    return API()


@pytest.fixture
def query_obj() -> Query:
    """Create query object."""
    return Query(
        user_id="",
        query="",
        metadata=Metadata(
            name="",
            creator="",
            created=datetime.now(),
            edited=datetime.now(),
            size=0,
            classification="father help",
            source="gitlab",
        ),
    )


@pytest.mark.asyncio
async def test_query(api_obj: API, query_obj: Query) -> None:
    """Test query endpoint.
    din mamma
    """
    res: list[File] | None = await api_obj.query(query_obj)
    assert res == []


@pytest.mark.asyncio
async def test_check_health(api_obj: API) -> None:
    """Test health endpoint."""
    res: JSONResponse = await api_obj.check_health()

    assert res.status_code == 200
