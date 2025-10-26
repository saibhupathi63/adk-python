"""Test to see if Gemini API rejects schemas with anyOf + other fields."""

from google.genai.types import Schema, Type
from pydantic import BaseModel, Field
from google.adk.tools._gemini_schema_util import _to_gemini_schema

class Person(BaseModel):
    name: str = Field(description="Person's name")
    age: int | None = Field(description="Person's age", ge=0)

# Generate the schema
pydantic_schema = Person.model_json_schema()
gemini_schema = _to_gemini_schema(pydantic_schema)

print("=== Analyzing the 'age' field schema ===")
age_schema = gemini_schema.properties['age']
print(f"Type: {age_schema.type}")
print(f"Description: {age_schema.description}")
print(f"Title: {age_schema.title}")
print(f"Has any_of: {age_schema.any_of is not None}")
if age_schema.any_of:
    print(f"Number of any_of options: {len(age_schema.any_of)}")
    for i, option in enumerate(age_schema.any_of):
        print(f"  Option {i}: type={option.type}, nullable={option.nullable}, minimum={option.minimum}")

print("\n=== The Problem ===")
print("The 'age' field has BOTH:")
print("1. any_of (the anyOf array)")
print("2. description, title, type fields")
print("\nGemini API requires: when using any_of, it must be the ONLY field set")
print("(besides potentially description/title at the top level)")
