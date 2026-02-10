from fastapi import FastAPI

from dmis_api.structures import DOWNSTREAM_STRUCTURE

app = FastAPI()


def validate_structure(validation_structure: list | dict, input_structure: list | dict) -> bool:
    """Validate some input structure against a defined structe."""


@app.get("/index")
async def root():
    return {}, 200
