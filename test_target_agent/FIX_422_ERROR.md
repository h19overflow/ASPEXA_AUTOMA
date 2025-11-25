# Fix for 422 Unprocessable Entity Error

## Problem
- FastAPI endpoint `/chat` receiving 422 Unprocessable Entity errors
- HTTP generator sends `{"prompt": "..."}` format
- Endpoint expected `{"message": "..."}` format
- Schema mismatch caused Pydantic validation failures

## Solution Implemented
- Updated `ChatRequest` model to accept both `message` and `prompt` fields
- Made both fields optional to support different client formats
- Added `@model_validator` decorator for cross-field validation
- Validator ensures at least one of `message` or `prompt` is provided
- Added `get_message()` helper method to extract value from either field
- Updated `/chat` endpoint handler to use `request.get_message()`
- Maintains backward compatibility with existing clients

## Files Modified
- `test_target_agent/main.py`: Updated ChatRequest model and endpoint handler

## Result
- Endpoint now accepts both `{"message": "..."}` and `{"prompt": "..."}` formats
- No more 422 errors from garak scanner requests
- Backward compatible with existing clients
- Proper validation ensures data integrity
- All linter checks pass
- No breaking changes to API contract
