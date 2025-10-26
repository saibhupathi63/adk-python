"""Test if google-genai properly unwraps anyOf for nullable types."""

from google.genai.types import JSONSchema, Schema
from pydantic import BaseModel, Field
import json

class Person(BaseModel):
    name: str = Field(description="Person's name")
    age: int | None = Field(description="Person's age", ge=0)

# Generate the Pydantic schema
pydantic_schema = Person.model_json_schema()

print("=== Original Pydantic Schema ===")
print(json.dumps(pydantic_schema, indent=2))

# Test: Call google-genai's Schema.from_json_schema directly
json_schema_obj = JSONSchema(**pydantic_schema)
gemini_schema = Schema.from_json_schema(
    json_schema=json_schema_obj,
    api_option='VERTEX_AI'
)

print("\n=== Gemini Schema (via google-genai directly) ===")
print(gemini_schema)

print("\n=== Analyzing 'age' field ===")
age_schema = gemini_schema.properties['age']
print(f"Type: {age_schema.type}")
print(f"Nullable: {age_schema.nullable}")
print(f"Has any_of: {age_schema.any_of is not None}")
if age_schema.any_of:
    print(f"Number of any_of options: {len(age_schema.any_of)}")
    for i, option in enumerate(age_schema.any_of):
        option_dict = option.model_dump(exclude_unset=True)
        print(f"  Option {i}: {option_dict}")

print("\n=== Test Summary ===")
if age_schema.any_of:
    print("❌ PROBLEM: anyOf was NOT unwrapped. This will cause Vertex AI error.")
    print("The schema has both any_of and other fields (type, description, title).")
else:
    print("✅ GOOD: anyOf was successfully unwrapped to nullable field.")
