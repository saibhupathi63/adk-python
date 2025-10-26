"""Test a potential fix for the nullable fields issue."""

from google.adk.tools._gemini_schema_util import (
    _sanitize_schema_formats_for_gemini,
    _dereference_schema,
    _ExtendedJSONSchema,
    _to_snake_case
)
from google.genai.types import Schema
from google.adk.utils.variant_utils import get_google_llm_variant
import json
from typing import Any

def _sanitize_schema_type_fixed(schema: dict[str, Any], in_any_of: bool = False) -> dict[str, Any]:
    """Fixed version that doesn't transform type:null inside anyOf."""
    if ("type" not in schema or not schema["type"]) and schema.keys().isdisjoint(schema):
        schema["type"] = "object"
    if isinstance(schema.get("type"), list):
        nullable = False
        non_null_type = None
        for t in schema["type"]:
            if t == "null":
                nullable = True
            elif not non_null_type:
                non_null_type = t
        if not non_null_type:
            non_null_type = "object"
        if nullable:
            schema["type"] = [non_null_type, "null"]
        else:
            schema["type"] = non_null_type
    elif schema.get("type") == "null":
        # FIX: Don't transform {"type": "null"} when inside anyOf
        # Let google-genai handle the unwrapping
        if not in_any_of:
            schema["type"] = ["object", "null"]

    return schema

def _sanitize_schema_formats_for_gemini_fixed(
    schema: dict[str, Any],
    in_any_of: bool = False
) -> dict[str, Any]:
    """Fixed version that tracks anyOf context."""
    supported_fields: set[str] = set(_ExtendedJSONSchema.model_fields.keys())
    supported_fields.discard("additional_properties")
    schema_field_names: set[str] = {"items"}
    list_schema_field_names: set[str] = {"any_of"}
    snake_case_schema = {}
    dict_schema_field_names: tuple[str, ...] = ("properties", "defs")

    for field_name, field_value in schema.items():
        field_name_snake = _to_snake_case(field_name)

        if field_name_snake in schema_field_names:
            snake_case_schema[field_name_snake] = _sanitize_schema_formats_for_gemini_fixed(
                field_value, in_any_of=in_any_of
            )
        elif field_name_snake in list_schema_field_names:
            # Mark that we're inside anyOf
            snake_case_schema[field_name_snake] = [
                _sanitize_schema_formats_for_gemini_fixed(value, in_any_of=True)
                for value in field_value
            ]
        elif field_name_snake in dict_schema_field_names and field_value is not None:
            snake_case_schema[field_name_snake] = {
                key: _sanitize_schema_formats_for_gemini_fixed(value, in_any_of=in_any_of)
                for key, value in field_value.items()
            }
        elif field_name_snake == "format" and field_value:
            current_type = schema.get("type")
            if (
                (current_type == "integer" or current_type == "number")
                and field_value in ("int32", "int64")
                or (current_type == "string" and field_value in ("date-time", "enum"))
            ):
                snake_case_schema[field_name_snake] = field_value
        elif field_name_snake in supported_fields and field_value is not None:
            snake_case_schema[field_name_snake] = field_value

    return _sanitize_schema_type_fixed(snake_case_schema, in_any_of=in_any_of)

# Test with the problematic schema
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

print("=== Original Approach (BROKEN) ===")
dereferenced = _dereference_schema(pydantic_schema)
sanitized_old = _sanitize_schema_formats_for_gemini(dereferenced)
print("Sanitized schema:")
print(json.dumps(sanitized_old['properties']['age'], indent=2))

json_schema_old = _ExtendedJSONSchema.model_validate(sanitized_old)
gemini_schema_old = Schema.from_json_schema(
    json_schema=json_schema_old,
    api_option=get_google_llm_variant()
)
age_old = gemini_schema_old.properties['age']
print(f"\nResult: type={age_old.type}, nullable={age_old.nullable}, has_any_of={age_old.any_of is not None}")
if age_old.any_of:
    print("❌ BROKEN: anyOf not unwrapped - will cause Vertex AI error")

print("\n=== Fixed Approach ===")
sanitized_new = _sanitize_schema_formats_for_gemini_fixed(pydantic_schema)
print("Sanitized schema:")
print(json.dumps(sanitized_new['properties']['age'], indent=2))

json_schema_new = _ExtendedJSONSchema.model_validate(sanitized_new)
gemini_schema_new = Schema.from_json_schema(
    json_schema=json_schema_new,
    api_option=get_google_llm_variant()
)
age_new = gemini_schema_new.properties['age']
print(f"\nResult: type={age_new.type}, nullable={age_new.nullable}, has_any_of={age_new.any_of is not None}")
if not age_new.any_of:
    print("✅ FIXED: anyOf unwrapped correctly - Vertex AI will accept this")
