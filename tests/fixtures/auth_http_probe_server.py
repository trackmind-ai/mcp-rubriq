# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/auth_http_probe_server.py

A streamable-HTTP MCP server protected by a Bearer token — the shape of every
hosted/remote MCP deployment. Requests without `Authorization: Bearer <token>`
get 401 and never reach the MCP layer.

Exists to prove MCP-Rubriq's --header flag end-to-end:
  - WITH the correct header  -> introspection succeeds (1 tool)
  - WITHOUT the header       -> actionable failure, not a hang or crash

Port via MCP_RUBRIQ_FIXTURE_PORT (default 8951); token via MCP_RUBRIQ_FIXTURE_TOKEN
(default "sekrit-token").

Run directly: python tests/fixtures/auth_http_probe_server.py
Then, e.g.:
  python plugins/mcp-rubriq/skills/mcp-rubriq/scripts/lint.py --transport http \
    --url http://127.0.0.1:8951/mcp --header "Authorization: Bearer sekrit-token"
"""

import os

from mcp.server.fastmcp import FastMCP

_PORT = int(os.environ.get("MCP_RUBRIQ_FIXTURE_PORT", "8951"))
_TOKEN = os.environ.get("MCP_RUBRIQ_FIXTURE_TOKEN", "sekrit-token")

mcp = FastMCP("mcp-rubriq-auth-http-probe", port=_PORT)


@mcp.tool()
def whoami() -> str:
    """Return the authenticated caller's identity string."""
    return "authenticated-user"


class BearerAuthMiddleware:
    """Minimal ASGI middleware: reject any HTTP request lacking the exact
    Bearer token before it reaches the MCP session manager."""

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
        BearerAuthMiddleware(mcp.streamable_http_app()),
        host="127.0.0.1",
        port=_PORT,
        log_level="warning",
    )
