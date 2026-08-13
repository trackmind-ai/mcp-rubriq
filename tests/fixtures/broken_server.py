# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/broken_server.py

A stdio "server" that fails immediately, in three selectable ways, to check
whether MCP-Rubriq surfaces an actionable message or dumps a raw traceback.
Selected via the MCP_RUBRIQ_FIXTURE_MODE env var:

  exit_nonzero (default) — exits with code 1 before any MCP handshake bytes
                            are written (e.g. a missing dependency, bad args).
  garbage_stdout          — writes non-JSON-RPC bytes to stdout, then exits.
  hang                    — never responds at all (relies on --timeout).

Run directly: python tests/fixtures/broken_server.py
"""

import os
import sys
import time

_MODE = os.environ.get("MCP_RUBRIQ_FIXTURE_MODE", "exit_nonzero")

if _MODE == "garbage_stdout":
    print("not json-rpc, just a plain crash message from a misconfigured server")
    sys.exit(1)
elif _MODE == "hang":
    time.sleep(3600)
else:  # exit_nonzero
    sys.stderr.write("fixture: simulated startup failure (e.g. missing dependency)\n")
    sys.exit(1)
