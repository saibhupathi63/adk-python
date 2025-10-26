# Issue #3281: Nullable Fields Broken with Google GenAI Bump

## Root Cause Analysis

### The Problem

When defining MCP tools with optional parameters using Pydantic's `int | None` or `str | None` type hints (OpenAPI 3.1 style), the Gemini API returns a 400 error:

```
Unable to submit request because `create_payee` functionDeclaration `parameters.person.age` schema specified other fields alongside any_of. When using any_of, it must be the only field set.
```

### The Bug

The issue is in **`_sanitize_schema_type` function** in [`src/google/adk/tools/_gemini_schema_util.py:96-97`](src/google/adk/tools/_gemini_schema_util.py#L96-L97):

```python
elif schema.get("type") == "null":
    schema["type"] = ["object", "null"]
```

This transformation breaks the `anyOf` unwrapping logic in `google-genai`'s `Schema.from_json_schema`.

### Detailed Flow

1. **Pydantic generates** (OpenAPI 3.1 style):
   ```json
   {
     "anyOf": [
       {"type": "integer", "minimum": 0},
       {"type": "null"}
     ],
     "description": "Person's age"
   }
   ```

2. **ADK's `_sanitize_schema_formats_for_gemini` recursively processes** the `anyOf` elements
   - First element `{"type": "integer", "minimum": 0}` → stays as-is
   - Second element `{"type": "null"}` → **transforms to `{"type": ["object", "null"]}`** (LINE 97)

3. **Result after sanitization**:
   ```json
   {
     "any_of": [
       {"type": "integer", "minimum": 0},
       {"type": ["object", "null"]}  ← PROBLEM!
     ],
     "description": "Person's age"
   }
   ```

4. **google-genai's unwrapping logic** (in `Schema.from_json_schema`, lines 2232-2250):
   - Expects: `{"type": "null"}` or `{"nullable": True}`
   - Gets: `{"type": ["object", "null"]}`
   - **Fails to unwrap** because it doesn't match the expected pattern

5. **Result**: Schema sent to Vertex AI has:
   ```
   any_of: [Schema(type=INTEGER), Schema(type=OBJECT, nullable=True)]
   description: "Person's age"
   type: OBJECT
   ```
   This violates Vertex AI's constraint: "when using any_of, it must be the only field set"

### Why This Line Exists

The `_sanitize_schema_type` function line 96-97 was likely added to handle standalone `{"type": "null"}` schemas, converting them to something Gemini can understand. However, it should **NOT** be applied to schemas that are part of an `anyOf` array used for representing nullable types.

### The Fix

The `_sanitize_schema_type` function should NOT transform `{"type": "null"}` when it's inside an `anyOf` array that's being used to represent nullable types. The google-genai library is designed to handle this unwrapping automatically.

**Recommended Solution**: Modify `_sanitize_schema_formats_for_gemini` to track when it's processing elements inside `any_of`, and skip the `{"type": "null"}` → `{"type": ["object", "null"]}` transformation in that context.

**Code Changes Required**:
1. Add an `in_any_of` parameter to `_sanitize_schema_formats_for_gemini` and `_sanitize_schema_type`
2. Set `in_any_of=True` when recursively processing elements of `any_of` lists
3. Skip the line 96-97 transformation when `in_any_of=True`
4. Update the test `test_sanitize_schema_formats_for_gemini_nullable` to expect `{"type": "null"}` instead of `{"type": ["object", "null"]}`
5. Add an end-to-end test using `_to_gemini_schema` to verify the anyOf unwrapping works correctly

**Alternative Solutions** (not recommended):
- **Option 2**: Remove all anyOf pre-processing and let google-genai handle everything (may break other cases)
- **Option 3**: Remove the line 96-97 transformation entirely (would break standalone `{"type": "null"}` schemas)

### Impact

- Affects all tools with optional parameters using Python 3.10+ union syntax (`Type | None`)
- Affects MCP tools particularly, as they often use optional parameters
- Regression introduced with google-genai v1.45.0+ which added stricter anyOf validation

### Workarounds

Until fixed, users can:
1. Avoid using optional parameters (not practical)
2. Downgrade google-genai to v1.44.0 (may have other implications)
3. Use OpenAPI 3.0 style with `required` field instead of nullable (breaks Pydantic patterns)

## Test Cases

See:
- `test_nullable_issue.py` - Demonstrates the original Pydantic schema
- `test_sanitize_issue.py` - Shows the problematic transformation
- `test_exact_adk_flow.py` - Confirms the unwrapping failure
- `test_anyof_unwrap.py` - Shows google-genai can unwrap when given correct input
