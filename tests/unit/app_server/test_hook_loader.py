"""Tests for hook_loader module.

This module tests the loading of hooks from the agent-server.
The app-server acts as a thin proxy that calls the agent-server's /api/hooks endpoint.
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from openhands.app_server.app_conversation.hook_loader import (
    load_project_hooks_from_agent_server,
)
from openhands.sdk.hooks import HookConfig


@pytest.mark.asyncio
async def test_load_project_hooks_successfully():
    hook_config = HookConfig.model_validate(
        {'session_start': [{'matcher': '*', 'hooks': [{'command': 'echo hi'}]}]}
    )

    mock_response = AsyncMock()
    mock_response.raise_for_status = Mock(return_value=None)
    mock_response.json = Mock(return_value={'hook_config': hook_config.model_dump()})

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient', return_value=mock_client) as mock_async_client:
        result = await load_project_hooks_from_agent_server(
            agent_server_url='http://agent-server:8000',
            session_api_key='test-key',
            project_dir='/workspace/repo',
        )

    assert isinstance(result, HookConfig)
    assert result.session_start[0].hooks[0].command == 'echo hi'

    mock_async_client.assert_called_once()
    mock_client.post.assert_called_once()
    _, kwargs = mock_client.post.call_args
    assert kwargs['headers']['X-Session-API-Key'] == 'test-key'
    assert kwargs['json']['project_dir'] == '/workspace/repo'


@pytest.mark.asyncio
async def test_load_project_hooks_returns_none_when_no_project_dir():
    result = await load_project_hooks_from_agent_server(
        agent_server_url='http://agent-server:8000',
        session_api_key='test-key',
        project_dir=None,
    )
    assert result is None


@pytest.mark.asyncio
async def test_load_project_hooks_returns_none_on_http_error():
    mock_response = AsyncMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        'boom',
        request=httpx.Request('POST', 'http://agent-server:8000/api/hooks'),
        response=httpx.Response(500, text='error'),
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient', return_value=mock_client):
        result = await load_project_hooks_from_agent_server(
            agent_server_url='http://agent-server:8000',
            session_api_key=None,
            project_dir='/workspace/repo',
        )

    assert result is None


@pytest.mark.asyncio
async def test_load_project_hooks_returns_none_when_hook_config_empty():
    hook_config = HookConfig.model_validate({})

    mock_response = AsyncMock()
    mock_response.raise_for_status = Mock(return_value=None)
    mock_response.json = Mock(return_value={'hook_config': hook_config.model_dump()})

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient', return_value=mock_client):
        result = await load_project_hooks_from_agent_server(
            agent_server_url='http://agent-server:8000',
            session_api_key=None,
            project_dir='/workspace/repo',
        )

    assert result is None


@pytest.mark.asyncio
async def test_load_project_hooks_returns_none_on_request_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(
        side_effect=httpx.RequestError(
            'boom',
            request=httpx.Request('POST', 'http://agent-server:8000/api/hooks'),
        )
    )

    with patch('httpx.AsyncClient', return_value=mock_client):
        result = await load_project_hooks_from_agent_server(
            agent_server_url='http://agent-server:8000',
            session_api_key=None,
            project_dir='/workspace/repo',
        )

    assert result is None


@pytest.mark.asyncio
async def test_load_project_hooks_does_not_send_session_api_key_header_when_missing():
    hook_config = HookConfig.model_validate(
        {'session_start': [{'matcher': '*', 'hooks': [{'command': 'echo hi'}]}]}
    )

    mock_response = AsyncMock()
    mock_response.raise_for_status = Mock(return_value=None)
    mock_response.json = Mock(return_value={'hook_config': hook_config.model_dump()})

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient', return_value=mock_client):
        await load_project_hooks_from_agent_server(
            agent_server_url='http://agent-server:8000',
            session_api_key=None,
            project_dir='/workspace/repo',
        )

    _, kwargs = mock_client.post.call_args
    assert 'X-Session-API-Key' not in kwargs['headers']
