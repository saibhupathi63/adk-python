"""Test if google-genai unwraps anyOf when description/title are present."""

from google.genai.types import JSONSchema, Schema
import json

# Test Case 1: anyOf WITHOUT description/title (should unwrap)
schema1_dict = {
    "any_of": [
        {"type": "integer", "minimum": 0},
        {"type": "null"}
    ]
}

print("=== Test 1: anyOf without description/title ===")
print("Input:", json.dumps(schema1_dict, indent=2))
json_schema1 = JSONSchema(**schema1_dict)
gemini_schema1 = Schema.from_json_schema(json_schema=json_schema1, api_option='VERTEX_AI')
print(f"Output type: {gemini_schema1.type}")
print(f"Output nullable: {gemini_schema1.nullable}")
print(f"Output any_of: {gemini_schema1.any_of}")
print(f"Result: {'✅ UNWRAPPED' if not gemini_schema1.any_of else '❌ NOT UNWRAPPED'}")

# Test Case 2: anyOf WITH description/title (will it unwrap?)
schema2_dict = {
    "any_of": [
        {"type": "integer", "minimum": 0},
        {"type": "null"}
    ],
    "description": "Person's age",
    "title": "Age"
}

print("\n=== Test 2: anyOf with description/title ===")
print("Input:", json.dumps(schema2_dict, indent=2))
json_schema2 = JSONSchema(**schema2_dict)
gemini_schema2 = Schema.from_json_schema(json_schema=json_schema2, api_option='VERTEX_AI')
print(f"Output type: {gemini_schema2.type}")
print(f"Output nullable: {gemini_schema2.nullable}")
print(f"Output description: {gemini_schema2.description}")
print(f"Output title: {gemini_schema2.title}")
print(f"Output any_of: {gemini_schema2.any_of}")
print(f"Result: {'✅ UNWRAPPED' if not gemini_schema2.any_of else '❌ NOT UNWRAPPED'}")

print("\n=== Conclusion ===")
if not gemini_schema1.any_of and not gemini_schema2.any_of:
    print("✅ Both cases unwrapped successfully")
elif not gemini_schema1.any_of and gemini_schema2.any_of:
    print("❌ PROBLEM: anyOf with description/title does NOT unwrap!")
    print("   This is the bug causing the Vertex AI error.")
elif gemini_schema1.any_of and not gemini_schema2.any_of:
    print("❓ Unexpected: only the second case unwrapped")
else:
    print("❌ Neither case unwrapped")
