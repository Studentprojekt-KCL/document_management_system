import json

from importlib import resources
import package_data

def get_file_resource():
    text = resources.read_text(package_data, "file_types.json")
    return json.loads(text)
