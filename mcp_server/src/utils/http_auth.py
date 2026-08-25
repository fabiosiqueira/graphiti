"""Bearer-token guard for the streamable HTTP transport.

The MCP SDK serves the transport over Starlette but ships no inbound
authentication, so a server that leaves localhost is open to anyone who can
reach the port. This wraps the SDK's ASGI app with a static-token check.

Written as pure ASGI rather than `BaseHTTPMiddleware`: the streamable HTTP
transport holds long-lived SSE responses open, and `BaseHTTPMiddleware` buffers
the response body, which would stall them.
"""

import hmac
from collections.abc import Iterable

from starlette.types import ASGIApp, Receive, Scope, Send

UNAUTHORIZED_BODY = b'{"error":"unauthorized"}'


class BearerAuthMiddleware:
    """Reject requests that do not carry the expected `Authorization: Bearer` token."""

    def __init__(self, app: ASGIApp, token: str, exempt_paths: Iterable[str] = ()) -> None:
        self.app = app
        self._token = token
        # Exact paths, never prefixes: `/health` must not exempt `/healthz`, and
        # a prefix match is the kind of thing that quietly widens later.
        self._exempt = frozenset(exempt_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http' or scope.get('path') in self._exempt:
            await self.app(scope, receive, send)
            return

        if not self._authorized(scope):
            await self._reject(send)
            return

        await self.app(scope, receive, send)

    def _authorized(self, scope: Scope) -> bool:
        for name, value in scope.get('headers', []):
            if name != b'authorization':
                continue
            scheme, _, credential = value.decode('latin-1').partition(' ')
            if scheme.lower() != 'bearer':
                return False
            return hmac.compare_digest(credential, self._token)
        return False

    async def _reject(self, send: Send) -> None:
        await send(
            {
                'type': 'http.response.start',
                'status': 401,
                'headers': [
                    (b'content-type', b'application/json'),
                    (b'content-length', str(len(UNAUTHORIZED_BODY)).encode()),
                    # Bare `Bearer`, with no `resource_metadata` parameter: that
                    # parameter is what makes an MCP client start an OAuth
                    # discovery flow (RFC 9728), and this server only speaks
                    # static tokens.
                    (b'www-authenticate', b'Bearer'),
                ],
            }
        )
        await send({'type': 'http.response.body', 'body': UNAUTHORIZED_BODY})


def apply_http_auth(app: ASGIApp, auth) -> ASGIApp:
    """Wrap `app` with the bearer guard when auth is enabled, else return it as is.

    `auth` is a `config.schema.AuthConfig`; it already refuses to validate with
    `enabled` set and no token, so no check for that is needed here.
    """
    if auth is None or not auth.enabled:
        return app
    return BearerAuthMiddleware(app, token=auth.token, exempt_paths=('/health',))
