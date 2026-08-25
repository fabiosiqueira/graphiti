#!/usr/bin/env python3
"""Unit tests for the DNS-rebinding allow-list on the HTTP transport.

FastMCP decides its transport-security policy inside `FastMCP.__init__`, from
whatever host it holds at that moment. This server builds `mcp` at import time
and only learns its real bind address later, when the config loads — so the
policy is always the loopback-flavoured one, and assigning `mcp.settings.host`
afterwards does not revisit it. Bound to a routable address, every request then
carries a Host header that the loopback allow-list cannot match and the SDK
answers 421 Misdirected Request.

These pin the policy as a function of configuration rather than of construction
order.
"""

import sys
from pathlib import Path

# Add the src directory to the path (mirrors the other unit tests)
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config.schema import ServerConfig  # noqa: E402
from graphiti_mcp_server import resolve_transport_security  # noqa: E402


def test_configured_hosts_enable_the_allow_list():
    settings = resolve_transport_security(
        ServerConfig(host='0.0.0.0', allowed_hosts=['graphiti-mcp.example.dev'])
    )
    assert settings is not None
    assert settings.enable_dns_rebinding_protection is True
    assert settings.allowed_hosts == ['graphiti-mcp.example.dev']


def test_public_bind_without_hosts_disables_protection():
    """The SDK's own default for a non-loopback bind — and the only alternative
    to 421 on every request, since the inherited allow-list holds only loopback."""
    settings = resolve_transport_security(ServerConfig(host='0.0.0.0'))
    assert settings is not None
    assert settings.enable_dns_rebinding_protection is False


def test_loopback_bind_is_left_alone():
    """Local setups keep FastMCP's own loopback allow-list; None means don't touch."""
    assert resolve_transport_security(ServerConfig(host='127.0.0.1')) is None


def test_comma_separated_hosts_are_split():
    """Env vars carry one string; the config field is a list."""
    config = ServerConfig(host='0.0.0.0', allowed_hosts='a.example.dev, b.example.dev')
    assert config.allowed_hosts == ['a.example.dev', 'b.example.dev']


def test_empty_string_means_no_hosts():
    """`${MCP_ALLOWED_HOSTS:}` resolves to None when unset — must not become ['']."""
    assert ServerConfig(host='0.0.0.0', allowed_hosts=None).allowed_hosts == []
    assert ServerConfig(host='0.0.0.0', allowed_hosts='').allowed_hosts == []
