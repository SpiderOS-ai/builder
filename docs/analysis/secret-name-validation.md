# Secret Name Validation Analysis

## Problem Statement

PR #12965 addressed a security issue where secret values were being exposed in error logs when `add_env_vars()` fails. The underlying failure occurs when users create secrets with names that are invalid for use as environment variables (e.g., `MY_DUMMY-SECRET` with a hyphen).

The error message was:
```
export MY_DUMMY-SECRET="blahblah"
bash: export: `MY_DUMMY-SECRET=blahblah': not a valid identifier
```

While PR #12965 correctly prevents secret values from leaking in error messages, this is a symptom-level fix. The **root cause** is that the APIs allow creating secrets with names that are invalid for use as environment variables.

## Analysis

### Environment Variable Naming Rules

According to POSIX standards and common shell implementations, valid environment variable names must:
1. **Start with** a letter (a-z, A-Z) or underscore (_)
2. **Contain only** alphanumeric characters (a-z, A-Z, 0-9) and underscores (_)

The regex pattern for validation: `^[a-zA-Z_][a-zA-Z0-9_]*$`

### Current State of Secret Management APIs

#### V0 API (Legacy - openhands/server/routes/secrets.py)

Located at `openhands/server/routes/secrets.py`, this API provides:
- `POST /api/secrets` - Create a new custom secret
- `PUT /api/secrets/{secret_id}` - Update a custom secret
- `GET /api/secrets` - List secret names
- `DELETE /api/secrets/{secret_id}` - Delete a secret

**Current validation**: Only checks if a secret name already exists (duplicate detection). **No validation of the secret name format**.

#### V1 API (New - openhands/app_server/)

The V1 API currently does not have dedicated endpoints for creating/updating custom secrets. Custom secrets are managed through the V0 API and retrieved via `UserContext.get_secrets()` which reads from the secrets store.

The V1 API has a `/api/v1/webhooks/secrets` endpoint in `webhook_router.py`, but this is for **retrieving** secrets by JWT token, not for creating/updating them.

### Existing Validation Pattern

The codebase already has validation for environment variable names in `openhands/core/config/mcp_config.py`:

```python
if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
    raise ValueError(
        f"Invalid environment variable name '{key}'. Must start with letter or underscore, contain only alphanumeric characters and underscores"
    )
```

This same validation pattern should be applied to custom secret names.

## Implementation Plan

### 1. Create Shared Validation Utility

Create a utility function that can be reused across the codebase:

**Location**: `openhands/utils/env_var_validation.py` (new file)

```python
import re

ENV_VAR_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def is_valid_env_var_name(name: str) -> bool:
    """Check if a name is valid for use as an environment variable."""
    return bool(ENV_VAR_NAME_PATTERN.match(name))

def validate_env_var_name(name: str) -> None:
    """Validate that a name is valid for use as an environment variable.
    
    Raises:
        ValueError: If the name is invalid.
    """
    if not is_valid_env_var_name(name):
        raise ValueError(
            f"Invalid name '{name}'. Must start with a letter or underscore, "
            "and contain only alphanumeric characters and underscores."
        )
```

### 2. Update V0 API (openhands/server/routes/secrets.py)

Add validation to:
- `POST /api/secrets` (create_custom_secret) - Validate `incoming_secret.name`
- `PUT /api/secrets/{secret_id}` (update_custom_secret) - Validate `incoming_secret.name`

### 3. Update Pydantic Model Validation (openhands/server/settings.py)

Add field validators to the Pydantic models:
- `CustomSecretWithoutValueModel` - Add validator for `name` field
- `CustomSecretModel` - Inherits from above, no additional changes needed

### 4. Update MCP Config Validation (openhands/core/config/mcp_config.py)

Refactor to use the shared validation utility for consistency.

### 5. Add Unit Tests

Add tests in `tests/unit/server/routes/test_secrets_api.py`:
- Test creating secret with invalid name returns 400
- Test updating secret with invalid name returns 400
- Test various invalid name patterns (hyphen, space, starts with digit, etc.)
- Test valid name patterns pass validation

Add tests for the validation utility in `tests/unit/test_env_var_validation.py`:
- Test various valid and invalid patterns

## Files to Modify

1. **New File**: `openhands/utils/env_var_validation.py` - Shared validation utility
2. **Modify**: `openhands/server/routes/secrets.py` - Add validation to create/update endpoints
3. **Modify**: `openhands/server/settings.py` - Add Pydantic field validator
4. **Modify**: `openhands/core/config/mcp_config.py` - Refactor to use shared utility
5. **Modify**: `tests/unit/server/routes/test_secrets_api.py` - Add validation tests
6. **New File**: `tests/unit/test_env_var_validation.py` - Tests for validation utility

## Error Messages

The API should return clear, actionable error messages:

- **HTTP 400 Bad Request** for invalid secret names
- Message: `"Invalid secret name '{name}'. Must start with a letter or underscore, and contain only alphanumeric characters and underscores."`

## Migration Considerations

- Existing secrets with invalid names will continue to exist in the store
- The validation only applies to new secret creation/updates
- Users with existing invalid secrets will need to delete and recreate them with valid names
- No migration script is needed; this is a forward-looking fix

## Summary

This fix prevents the problem at its source - ensuring that only valid environment variable names can be used as secret names. Combined with PR #12965's fix that sanitizes error messages, this provides defense in depth against secret value exposure.
