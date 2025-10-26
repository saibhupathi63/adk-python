"""Test the EXACT flow that ADK uses, including the problematic transformation."""

from google.genai.types import JSONSchema, Schema
from google.adk.tools._gemini_schema_util import (
    _sanitize_schema_formats_for_gemini,
    _dereference_schema,
    _ExtendedJSONSchema
)
from google.adk.utils.variant_utils import get_google_llm_variant
import json

# This is what Pydantic generates for int | None
pydantic_schema = {
    "properties": {
        "age": {
            "anyOf": [
                {"minimum": 0, "type": "integer"},
                {"type": "null"}
            ],
            "description": "Person's age",
            "title": "Age"
        }
    },
    "type": "object"
}

print("=== Step 1: Original Pydantic Schema ===")
print(json.dumps(pydantic_schema, indent=2))

# ADK processing
dereferenced = _dereference_schema(pydantic_schema)
print("\n=== Step 2: After _dereference_schema ===")
print(json.dumps(dereferenced, indent=2))

sanitized = _sanitize_schema_formats_for_gemini(dereferenced)
print("\n=== Step 3: After _sanitize_schema_formats_for_gemini ===")
print(json.dumps(sanitized, indent=2))

# The key problem: note the 'age' field after sanitization
print("\n=== Critical Issue in 'age' field ===")
age_sanitized = sanitized['properties']['age']
print(json.dumps(age_sanitized, indent=2))
print(f"\nNotice: The second element of any_of has type={age_sanitized['any_of'][1]['type']}")
print("It's ['object', 'null'] instead of just 'null'!")
print("This is due to _sanitize_schema_type being called on {'type': 'null'}")

# Now convert to Gemini schema
print("\n=== Step 4: Converting to Gemini Schema ===")
try:
    json_schema_obj = _ExtendedJSONSchema.model_validate(sanitized)
    gemini_schema = Schema.from_json_schema(
        json_schema=json_schema_obj,
        api_option=get_google_llm_variant()
    )
    print("Gemini Schema for 'age':")
    age_schema = gemini_schema.properties['age']
    print(f"  Type: {age_schema.type}")
    print(f"  Nullable: {age_schema.nullable}")
    print(f"  any_of: {age_schema.any_of}")

    if age_schema.any_of:
        print("\n❌ PROBLEM CONFIRMED!")
        print("The schema was NOT unwrapped because:")
        print("  The second element is {'type': ['object', 'null']} instead of {'type': 'null'}")
        print("  So it doesn't match the unwrapping condition")
        for i, option in enumerate(age_schema.any_of):
            option_dict = option.model_dump(exclude_unset=True)
            print(f"  Option {i}: {option_dict}")
    else:
        print("\n✅ Schema was unwrapped successfully")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
