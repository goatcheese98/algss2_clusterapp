"""Validate CycloneDX 1.6 using its tagged official schema; verified HTTPS only."""
import json
from pathlib import Path
import sys
import urllib.request
import warnings
import jsonschema

# Official 1.6 specification commit, not a moving branch.
REVISION = '55343ba19dee1785acf1ce9191540d5fd7b590db'
base = f'https://raw.githubusercontent.com/CycloneDX/specification/{REVISION}/schema/'
schemas = {}
for name in ('bom-1.6.schema.json', 'spdx.schema.json', 'jsf-0.82.schema.json'):
    with urllib.request.urlopen(base + name, timeout=60) as response:
        schemas[name] = json.load(response)
store = {base + name: schema for name, schema in schemas.items()}
for name, schema in schemas.items():
    if '$id' in schema:
        store[schema['$id']] = schema
with warnings.catch_warnings():
    warnings.simplefilter('ignore', DeprecationWarning)
    resolver = jsonschema.RefResolver(base_uri=base + 'bom-1.6.schema.json', referrer=schemas['bom-1.6.schema.json'], store=store)
    jsonschema.Draft7Validator(schemas['bom-1.6.schema.json'], resolver=resolver).validate(json.loads(Path(sys.argv[1]).read_text()))
print(f'CycloneDX 1.6 official schema validation passed ({REVISION})')
