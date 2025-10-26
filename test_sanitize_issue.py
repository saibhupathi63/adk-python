"""Test to see what _sanitize_schema_formats_for_gemini does to anyOf fields."""

from pydantic import BaseModel, Field
from google.adk.tools._gemini_schema_util import (
    _sanitize_schema_formats_for_gemini,
    _to_gemini_schema,
    _dereference_schema
)
import json

class Person(BaseModel):
    name: str = Field(description="Person's name")
    age: int | None = Field(description="Person's age", ge=0)

# Generate the Pydantic schema
pydantic_schema = Person.model_json_schema()

print("=== Step 1: Original Pydantic Schema ===")
print(json.dumps(pydantic_schema, indent=2))

print("\n=== Step 2: After _dereference_schema ===")
dereferenced = _dereference_schema(pydantic_schema)
print(json.dumps(dereferenced, indent=2))

print("\n=== Step 3: After _sanitize_schema_formats_for_gemini ===")
sanitized = _sanitize_schema_formats_for_gemini(dereferenced)
print(json.dumps(sanitized, indent=2))

print("\n=== Analysis of 'age' field transformation ===")
print("Original age field:")
print(json.dumps(pydantic_schema['properties']['age'], indent=2))
print("\nSanitized age field:")
print(json.dumps(sanitized['properties']['age'], indent=2))

print("\n=== Key Observation ===")
original_age = pydantic_schema['properties']['age']
sanitized_age = sanitized['properties']['age']

if 'anyOf' in original_age and 'any_of' in sanitized_age:
    print("✅ anyOf was converted to any_of (snake_case)")
    print(f"  - Original has 'anyOf' at top level with description/title")
    print(f"  - Sanitized has 'any_of' at top level with description/title")
    print("  - ⚠️  This structure (any_of + other fields) is problematic for Vertex AI!")
elif 'anyOf' in original_age and 'any_of' not in sanitized_age:
    print("❓ anyOf was removed or transformed")
else:
    print("❓ Unexpected state")
