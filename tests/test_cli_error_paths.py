# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later

"""
tests/test_cli_error_paths.py

Regression tests for lint.py's error handling at the real CLI boundary —
invoked as a subprocess exactly as the matrix runner and SKILL.md do, not
through internal functions. These paths were manually verified to degrade
cleanly (clean JSON error, not a raw traceback) but had NO automated test
pinning that behavior, so a future change could silently reintroduce a
crash.

Deliberately excludes shell-injection / malicious-input attempts (--command
with shell metacharacters, path traversal) — those belong to adversarial
testing, not baseline correctness.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
LINT_SCRIPT = REPO_ROOT / "plugins" / "mcp-rubriq" / "skills" / "mcp-rubriq" / "scripts" / "lint.py"


def _run(*args: str, timeout: int = 15) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(LINT_SCRIPT), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _error_json(stderr: str) -> dict:
    return json.loads(stderr.strip())


class TestMissingRequiredArgs:
    def test_stdio_without_command(self):
        code, _, stderr = _run("--transport", "stdio", "--timeout", "5")
        assert code == 1
        assert "command" in _error_json(stderr)["error"].lower()

    def test_http_without_url(self):
        code, _, stderr = _run("--transport", "http", "--timeout", "5")
        assert code == 1
        assert "url" in _error_json(stderr)["error"].lower()

    def test_sse_without_url(self):
        code, _, stderr = _run("--transport", "sse", "--timeout", "5")
        assert code == 1
        assert "url" in _error_json(stderr)["error"].lower()


class TestMalformedFlagValues:
    def test_env_without_equals_sign(self):
        """A typo'd --env (forgot the '=') must produce a clean JSON error
        via lint.py's own exception handler, not an uncaught ValueError
        traceback — this is the real CLI path, not the unit-level
        _parse_env test in test_cli_parsing.py."""
        code, _, stderr = _run(
            "--transport",
            "stdio",
            "--command",
            "python tests/fixtures/sample_server.py",
            "--env",
            "NOTAPAIR",
            "--timeout",
            "5",
        )
        assert code == 1
        err = _error_json(stderr)
        assert err["detail"] == "ValueError"
        assert "NOTAPAIR" in err["error"]

    def test_header_without_colon(self):
        code, _, stderr = _run(
            "--transport",
            "http",
            "--url",
            "http://127.0.0.1:1/mcp",
            "--header",
            "NotAHeader",
            "--timeout",
            "5",
        )
        assert code == 1
        err = _error_json(stderr)
        assert err["detail"] == "ValueError"

    def test_timeout_zero_times_out_cleanly(self):
        """A zero timeout must produce the actionable timeout message, not
        hang or crash — it's a degenerate but valid value, not a parse error."""
        code, _, stderr = _run(
            "--transport",
            "stdio",
            "--command",
            "python tests/fixtures/sample_server.py",
            "--timeout",
            "0",
        )
        assert code == 1
        err = _error_json(stderr)
        assert "timed out" in err["error"].lower()
        assert err["detail"] == "Increase --timeout or verify the server is reachable."


class TestUnresolvableTargets:
    def test_nonexistent_binary(self):
        """A typo'd command name (the single most common real mistake) must
        surface as a clean, named FileNotFoundError, not a raw traceback."""
        code, _, stderr = _run(
            "--transport",
            "stdio",
            "--command",
            "this_binary_does_not_exist_xyz_12345",
            "--timeout",
            "5",
        )
        assert code == 1
        err = _error_json(stderr)
        assert err["detail"] == "FileNotFoundError"

    def test_connection_refused_http(self):
        code, _, stderr = _run(
            "--transport",
            "http",
            "--url",
            "http://127.0.0.1:1/mcp",
            "--timeout",
            "5",
        )
        assert code == 1
        err = _error_json(stderr)
        assert err["detail"] == "ServerConnectionError"
