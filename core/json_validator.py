import json
from pathlib import Path
from jsonschema import validate, ValidationError


def validate_json(json_input):
    schema_path = Path(__file__).parent / "core" / "scl_schema.json"
    with open(schema_path, 'r') as f:
        schema = json.load(f)    
    if isinstance(json_input, str):
        try:
            json_data = json.loads(json_input)
        except json.JSONDecodeError:
            return False
    else:
        json_data = json_input
    try:
        validate(instance=json_data, schema=schema)
        return True
    except ValidationError:
        return False