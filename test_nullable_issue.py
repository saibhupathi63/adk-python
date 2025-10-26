"""Test script to reproduce the nullable fields issue with Pydantic and Gemini schema conversion."""

from pydantic import BaseModel, Field
from google.adk.tools._gemini_schema_util import _to_gemini_schema
import json

class Person(BaseModel):
    name: str = Field(description="Person's name")
    age: int | None = Field(description="Person's age", ge=0)
    email: str | None = Field(description="Person's email address")
    occupation: str | None = Field(description="Person's occupation")

# Generate the Pydantic JSON schema
pydantic_schema = Person.model_json_schema()
print("=== Pydantic JSON Schema ===")
print(json.dumps(pydantic_schema, indent=2))

# Convert to Gemini schema
print("\n=== Attempting to convert to Gemini Schema ===")
try:
    gemini_schema = _to_gemini_schema(pydantic_schema)
    print("Success! Gemini Schema:")
    print(gemini_schema)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# Check what's happening with the age field specifically
print("\n=== Age field analysis ===")
age_field = pydantic_schema.get("properties", {}).get("age", {})
print(json.dumps(age_field, indent=2))
