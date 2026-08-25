#!/usr/bin/env python3
"""Unit tests: a client that cannot be built must stop the server, not be skipped.

`GraphitiService.initialize` used to catch LLM and embedder construction errors
and log a warning, leaving the client as None. graphiti-core then substitutes
its own default OpenAI client — so a server misconfigured for OpenRouter came up
"healthy", accepted writes, and shipped the OpenRouter key to api.openai.com,
where every episode died with 401 inside the background worker. From a client
the failure is invisible: `add_memory` returns 200 and the episode never
appears.

The reranker path in the same function already states this invariant ("setup
errors must remain fatal rather than silently restoring that default"). These
tests extend it to the other two clients.
"""

import sys
from pathlib import Path

import pytest

# Add the src directory to the path (mirrors the other unit tests)
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import graphiti_mcp_server as server  # noqa: E402
from config.schema import GraphitiConfig  # noqa: E402


def _boom(*args, **kwargs):
    raise TypeError("__init__() got an unexpected keyword argument 'structured_output_mode'")


@pytest.mark.asyncio
async def test_llm_client_failure_stops_startup(monkeypatch):
    monkeypatch.setattr(server.LLMClientFactory, 'create', staticmethod(_boom))
    service = server.GraphitiService(GraphitiConfig())
    with pytest.raises(Exception, match='structured_output_mode'):
        await service.initialize()


@pytest.mark.asyncio
async def test_embedder_client_failure_stops_startup(monkeypatch):
    monkeypatch.setattr(server.LLMClientFactory, 'create', staticmethod(lambda *a, **k: object()))
    monkeypatch.setattr(server.EmbedderFactory, 'create', staticmethod(_boom))
    service = server.GraphitiService(GraphitiConfig())
    with pytest.raises(Exception, match='structured_output_mode'):
        await service.initialize()
