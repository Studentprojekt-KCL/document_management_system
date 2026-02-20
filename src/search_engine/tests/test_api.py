from fastapi.responses import JSONResponse
from se_api import api, models
import pytest


@pytest.fixture
def api_obj():
    return api.API()


@pytest.fixture
def query_obj():
    return models.Query(user_id="", query="", metadata=models.Metadata(name="", author="", version=""))


@pytest.mark.asyncio
async def test_query(api_obj: api.API, query_obj: models.Query):
    res: list[models.File] | None = await api_obj.query(query_obj)
    assert res == []


@pytest.mark.asyncio
async def test_check_health(api_obj: api.API):
    res: JSONResponse = await api_obj.check_health()

    assert res.status_code == 200
