#!/usr/bin/env python3
"""Unit tests for the bearer-token guard on the HTTP transport.

The MCP server binds a public address once it leaves the developer's machine,
and the transport ships with no inbound authentication of its own. These tests
pin the guard's contract: it rejects anything without an exact token, it leaves
`/health` open so container orchestrators can still probe liveness, and it is
inert unless explicitly enabled — so the default local setup keeps working.
"""

import sys
from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

# Add the src directory to the path (mirrors the other unit tests)
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config.schema import AuthConfig, ServerConfig  # noqa: E402
from utils.http_auth import BearerAuthMiddleware, apply_http_auth  # noqa: E402

TOKEN = 'sk-graphiti-test-0123456789abcdef'


def _inner_app() -> Starlette:
    """Stand-in for `mcp.streamable_http_app()` — same ASGI contract, no server."""

    async def ok(request):
        return JSONResponse({'reached': request.url.path})

    return Starlette(
        routes=[
            Route('/mcp/', ok, methods=['GET', 'POST']),
            Route('/health', ok),
            Route('/healthz', ok),
        ]
    )


@pytest.fixture
def guarded() -> TestClient:
    app = BearerAuthMiddleware(_inner_app(), token=TOKEN, exempt_paths=('/health',))
    return TestClient(app)


# ── The guard rejects ─────────────────────────────────────────────────────────


def test_missing_header_is_rejected(guarded):
    response = guarded.post('/mcp/')
    assert response.status_code == 401
    # RFC 7235 requires a challenge; keep it a bare `Bearer` so MCP clients do
    # not read a `resource_metadata` parameter and start an OAuth discovery
    # dance against a server that only speaks static tokens.
    assert response.headers['www-authenticate'] == 'Bearer'


def test_wrong_token_is_rejected(guarded):
    response = guarded.post('/mcp/', headers={'Authorization': 'Bearer wrong-token'})
    assert response.status_code == 401


def test_token_prefix_is_rejected(guarded):
    """A truncated token must not pass — the comparison is whole-value."""
    response = guarded.post('/mcp/', headers={'Authorization': f'Bearer {TOKEN[:-1]}'})
    assert response.status_code == 401


def test_wrong_scheme_is_rejected(guarded):
    """Basic credentials are not bearer credentials, even when the value matches."""
    response = guarded.post('/mcp/', headers={'Authorization': f'Basic {TOKEN}'})
    assert response.status_code == 401


def test_bare_token_without_scheme_is_rejected(guarded):
    response = guarded.post('/mcp/', headers={'Authorization': TOKEN})
    assert response.status_code == 401


# ── The guard admits ──────────────────────────────────────────────────────────


def test_correct_token_passes(guarded):
    response = guarded.post('/mcp/', headers={'Authorization': f'Bearer {TOKEN}'})
    assert response.status_code == 200
    assert response.json() == {'reached': '/mcp/'}


def test_scheme_is_case_insensitive(guarded):
    """RFC 7235 makes the auth scheme case-insensitive; the token is not."""
    response = guarded.post('/mcp/', headers={'Authorization': f'bearer {TOKEN}'})
    assert response.status_code == 200


# ── Exemptions ────────────────────────────────────────────────────────────────


def test_health_is_exempt(guarded):
    """Coolify's healthcheck has no token; locking /health locks out the deploy."""
    response = guarded.get('/health')
    assert response.status_code == 200


def test_exemption_matches_the_whole_path(guarded):
    """`/healthz` must not inherit `/health`'s exemption by prefix."""
    response = guarded.get('/healthz')
    assert response.status_code == 401


# ── Wiring ────────────────────────────────────────────────────────────────────


def test_apply_http_auth_is_inert_when_disabled():
    """Default local setup: no auth configured, app returned untouched."""
    app = _inner_app()
    assert apply_http_auth(app, ServerConfig().auth) is app


def test_apply_http_auth_wraps_when_enabled():
    app = _inner_app()
    wrapped = apply_http_auth(app, AuthConfig(enabled=True, token=TOKEN))
    assert isinstance(wrapped, BearerAuthMiddleware)
    assert TestClient(wrapped).post('/mcp/').status_code == 401


def test_enabling_auth_without_a_token_fails_loudly():
    """Better to refuse to boot than to serve an open port that reads secured."""
    with pytest.raises(ValueError, match='token'):
        AuthConfig(enabled=True, token=None)


def test_auth_defaults_to_disabled():
    assert ServerConfig().auth.enabled is False
