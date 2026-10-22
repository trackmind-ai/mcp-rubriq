# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later

"""
tests/fixtures/auth_sse_probe_server.py

The SSE-transport twin of auth_http_probe_server.py. --header plumbing was
added identically to both sse_client and streamablehttp_client, but SSE's
connection mechanics (a long-lived GET stream + separate POST channel) differ
enough from streamable HTTP under the hood that HTTP-only testing doesn't
prove SSE works — this fixture closes that gap directly.

Port via MCP_RUBRIQ_FIXTURE_PORT (default 8954); token via MCP_RUBRIQ_FIXTURE_TOKEN
(default "sekrit-token").

Run directly: python tests/fixtures/auth_sse_probe_server.py
Then, e.g.:
  python plugins/mcp-rubriq/skills/mcp-rubriq/scripts/lint.py --transport sse \
    --url http://127.0.0.1:8954/sse --header "Authorization: Bearer sekrit-token"
"""

import os

from mcp.server.fastmcp import FastMCP

_PORT = int(os.environ.get("MCP_RUBRIQ_FIXTURE_PORT", "8954"))
_TOKEN = os.environ.get("MCP_RUBRIQ_FIXTURE_TOKEN", "sekrit-token")

mcp = FastMCP("mcp-rubriq-auth-sse-probe", port=_PORT)


@mcp.tool()
def whoami() -> str:
    """Return the authenticated caller's identity string."""
    return "authenticated-user"


class BearerAuthMiddleware:
    """Minimal ASGI middleware: reject any HTTP request lacking the exact
    Bearer token before it reaches the MCP session manager. Same shape as
    auth_http_probe_server.py's — SSE's app is ASGI too, so the same
    middleware wraps it."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = {k.decode().lower(): v.decode() for k, v in (scope.get("headers") or [])}
            if headers.get("authorization") != f"Bearer {_TOKEN}":
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"text/plain"),
                            (b"www-authenticate", b"Bearer"),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": b"unauthorized"})
                return
        await self.app(scope, receive, send)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        BearerAuthMiddleware(mcp.sse_app()),
        host="127.0.0.1",
        port=_PORT,
        log_level="warning",
    )
