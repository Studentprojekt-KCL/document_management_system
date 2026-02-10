from fastapi import FastAPI
from typing import Any

from dmis_api.structures import DOWNSTREAM_STRUCTURE

app = FastAPI()

def validate_structure(validation_structure: list | dict | None, input_structure: list | dict) -> bool:
    """Validate some input structure against a defined structure."""
    if not validation_structure:
        return False
    result = True
    if isinstance(validation_structure, type):
        if validation_structure == Any:
            return True
        return isinstance(input_structure, validation_structure)

    if isinstance(input_structure, dict | list):
        for key in input_structure:
            result &= validate_structure(validation_structure.get(key), input_structure.get(key))
        return result
    if isinstance(input_structure, list):
        for index, value in enumerate(input_structure):
            result &= validate_structure(validation_structure[index], value)
        return result
    return result

@app.get("/index", status_code=200)
async def index():
    if not validate_structure(DOWNSTREAM_STRUCTURE):
        return {}
    return {}
