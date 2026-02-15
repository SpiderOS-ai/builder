"""Utilities for loading hooks for V1 conversations.

V1 app-server does not directly access the remote workspace filesystem, so it
delegates hook loading to the agent-server.

This mirrors the existing skill loading design in skill_loader.py:
- app-server computes the project_dir inside the workspace
- app-server calls the agent-server /api/hooks endpoint
- app-server merges the returned HookConfig into StartConversationRequest

We intentionally default to NOT loading user hooks in the app-server.
"""

from __future__ import annotations

import logging

import httpx
from pydantic import BaseModel, Field

from openhands.sdk.hooks import HookConfig

_logger = logging.getLogger(__name__)


class HooksRequest(BaseModel):
    project_dir: str | None = Field(
        default=None, description='Workspace directory path for project hooks'
    )


class HooksResponse(BaseModel):
    hook_config: HookConfig | None = Field(
        default=None,
        description='Hook configuration loaded from the workspace, or None if not found',
    )


async def load_project_hooks_from_agent_server(
    *,
    agent_server_url: str,
    session_api_key: str | None,
    project_dir: str | None,
) -> HookConfig | None:
    """Load project hooks from the agent-server.

    Args:
        agent_server_url: URL of the agent server (e.g., 'http://localhost:8000')
        session_api_key: Session API key for authentication (optional)
        project_dir: Workspace directory path for project hooks

    Returns:
        HookConfig if present and valid, else None.

        Returns None when:
        - project_dir is not provided
        - hooks.json is missing/empty
        - the agent-server returns an error or is unreachable
    """
    if not project_dir:
        return None

    try:
        payload = HooksRequest(project_dir=project_dir).model_dump()

        headers = {'Content-Type': 'application/json'}
        if session_api_key:
            headers['X-Session-API-Key'] = session_api_key

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{agent_server_url}/api/hooks',
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        hooks_response = HooksResponse.model_validate(data)
        hook_config = hooks_response.hook_config
        if hook_config is not None and hook_config.is_empty():
            return None

        _logger.info(
            'Loaded project hooks from agent-server: %s',
            'present' if hook_config is not None else 'none',
        )
        return hook_config

    except httpx.HTTPStatusError as e:
        _logger.warning(
            'Agent-server returned error status %s for /api/hooks: %s',
            e.response.status_code,
            e.response.text,
        )
        return None
    except httpx.RequestError as e:
        _logger.warning('Failed to connect to agent-server for /api/hooks: %s', e)
        return None
    except Exception as e:
        _logger.warning('Failed to load hooks from agent-server: %s', e)
        return None
