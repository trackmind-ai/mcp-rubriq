# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/protocol_breaker_server.py

A raw JSON-RPC-over-stdio "MCP server" (no SDK) that completes the initialize
handshake CORRECTLY — advertising tools, resources, and prompts — and then
misbehaves on the very next request. Complements broken_server.py, which
fails *before* the handshake; every failure here happens *mid-session*, a
region no existing fixture reaches.

Modes via MCP_RUBRIQ_FIXTURE_MODE:

  crash_after_init (default) — exits(1) when the first post-handshake request
                                (tools/list) arrives. Simulates a server that
                                initializes fine but dies on first real use.
  garbage_after_init          — answers tools/list with a non-JSON line, then
                                exits. Simulates mid-stream protocol corruption.
  hang_after_init             — never answers any post-handshake request.
                                Exercises the per-call timeout inside
                                _introspect_session (not the connect timeout).
  old_protocol                — negotiates the OLDEST spec version the client
                                SDK supports (2024-11-05) and then behaves
                                correctly (serves one tool). A server on an
                                old-but-supported protocol must lint fine.
  alien_protocol              — claims a protocol version no client supports
                                ("2019-01-01"). The client must reject it with
                                an actionable error, not crash or mis-lint.
  false_advertising           — advertises tools+resources+prompts correctly,
                                but tools/list itself returns "Method not
                                found" while resources/prompts list fine.
                                Distinct from the templates-optional case:
                                an ADVERTISED capability whose own listing is
                                unimplemented is a genuine server bug that
                                must be recorded as a warning, not silently
                                treated as "zero tools".

Implemented raw (readline/write) because the SDK cannot be told to violate
its own protocol.

Run directly: python tests/fixtures/protocol_breaker_server.py
"""

import json
import os
import sys
import time

_MODE = os.environ.get("MCP_RUBRIQ_FIXTURE_MODE", "crash_after_init")


def _read_message():
    line = sys.stdin.readline()
    if not line:
        sys.exit(0)  # client closed stdin — normal shutdown
    return json.loads(line)


def _write_message(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main() -> None:
    # Phase 1: perform the initialize handshake.
    while True:
        msg = _read_message()
        if msg.get("method") == "initialize":
            if _MODE == "old_protocol":
                version = "2024-11-05"  # oldest version modern client SDKs accept
            elif _MODE == "alien_protocol":
                version = "2019-01-01"  # no client supports this
            else:
                version = msg["params"]["protocolVersion"]  # echo — correct handshake
            # old_protocol behaves honestly: advertise only what it implements
            # (tools). The other modes advertise everything precisely so the
            # failed/missing listings are visible against the advertised surface.
            capabilities = (
                {"tools": {}}
                if _MODE == "old_protocol"
                else {"tools": {}, "resources": {}, "prompts": {}}
            )
            _write_message(
                {
                    "jsonrpc": "2.0",
                    "id": msg["id"],
                    "result": {
                        "protocolVersion": version,
                        "capabilities": capabilities,
                        "serverInfo": {"name": "mcp-rubriq-protocol-breaker", "version": "0.0.1"},
                    },
                }
            )
            break

    # Phase 2: behave per mode on post-handshake requests.
    while True:
        msg = _read_message()
        if msg.get("method") == "notifications/initialized":
            continue  # notification, no response required
        if "id" not in msg:
            continue

        if _MODE == "old_protocol":
            # Behave CORRECTLY on the old protocol: serve one tool, answer
            # everything else with the standard "method not found".
            if msg.get("method") == "tools/list":
                _write_message(
                    {
                        "jsonrpc": "2.0",
                        "id": msg["id"],
                        "result": {
                            "tools": [
                                {
                                    "name": "legacy_ping",
                                    "description": (
                                        "Trivial tool served over the oldest supported "
                                        "protocol version."
                                    ),
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {},
                                        "required": [],
                                    },
                                }
                            ]
                        },
                    }
                )
            else:
                _write_message(
                    {
                        "jsonrpc": "2.0",
                        "id": msg["id"],
                        "error": {"code": -32601, "message": "Method not found"},
                    }
                )
        elif _MODE == "false_advertising":
            # tools/list is the one advertised method that's actually broken.
            # resources/prompts work fine, to prove the failure is attributed
            # to tools specifically, not a blanket connection problem.
            if msg.get("method") == "tools/list":
                _write_message(
                    {
                        "jsonrpc": "2.0",
                        "id": msg["id"],
                        "error": {"code": -32601, "message": "Method not found"},
                    }
                )
            elif msg.get("method") == "resources/list":
                _write_message({"jsonrpc": "2.0", "id": msg["id"], "result": {"resources": []}})
            elif msg.get("method") == "resources/templates/list":
                _write_message(
                    {"jsonrpc": "2.0", "id": msg["id"], "result": {"resourceTemplates": []}}
                )
            elif msg.get("method") == "prompts/list":
                _write_message(
                    {
                        "jsonrpc": "2.0",
                        "id": msg["id"],
                        "result": {
                            "prompts": [
                                {
                                    "name": "still_works",
                                    "description": "Proves only tools/list is broken.",
                                }
                            ]
                        },
                    }
                )
            else:
                _write_message(
                    {
                        "jsonrpc": "2.0",
                        "id": msg["id"],
                        "error": {"code": -32601, "message": "Method not found"},
                    }
                )
        elif _MODE == "garbage_after_init":
            sys.stdout.write("this is not json-rpc — mid-session corruption\n")
            sys.stdout.flush()
            sys.exit(1)
        elif _MODE == "hang_after_init":
            time.sleep(3600)
        else:  # crash_after_init (alien_protocol never gets here — client aborts)
            sys.stderr.write("fixture: simulated crash after successful initialize\n")
            sys.stderr.flush()
            sys.exit(1)


if __name__ == "__main__":
    main()
