# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later

"""
tests/test_cli_parsing.py

Unit tests for the CLI-facing parsing helpers in introspection/introspect.py:
split_command (the G7 Windows-backslash fix) and _parse_env. These sit on the
exact boundary where SKILL.md hands user-resolved commands to the pipeline —
the historically bug-dense seam (G7, G11).
"""

import sys

import pytest
from introspection.introspect import (
    _parse_env,
    _parse_headers,
    _unwrap_exception_group,
    split_command,
)

if sys.version_info < (3, 11):
    # BaseExceptionGroup is a real builtin from 3.11 on; below that it only exists
    # because the `exceptiongroup` backport (a declared runtime dependency for
    # python_version<'3.11', see introspection/requirements.txt) injects it into
    # `builtins`. Importing it explicitly here keeps this test correct on the
    # project's stated 3.10 floor, not just on whatever Python happens to run it.
    from exceptiongroup import BaseExceptionGroup


class TestSplitCommand:
    def test_simple_command(self):
        assert split_command("python my_server.py") == ["python", "my_server.py"]

    def test_windows_backslash_path_preserved(self):
        """Regression: POSIX-mode shlex silently stripped backslashes,
        turning C:\\Users\\x into C:Usersx — a different, still-valid-looking,
        WRONG path with no error raised."""
        tokens = split_command(r"npx -y @modelcontextprotocol/server-filesystem C:\Users\Public")
        assert tokens[-1] == r"C:\Users\Public"

    def test_double_quoted_token_unwrapped(self):
        tokens = split_command('npx -y pkg "C:\\Users\\Jane Doe\\project"')
        assert tokens[-1] == "C:\\Users\\Jane Doe\\project"

    def test_single_quoted_token_unwrapped(self):
        tokens = split_command("python 'my server.py'")
        assert tokens[-1] == "my server.py"

    def test_empty_string(self):
        """Documents current behavior: empty command splits to an empty list.
        (Callers index parts[0]; the resulting IndexError is caught by their
        generic error handler — flagged as a UX-polish candidate, not a crash.)"""
        assert split_command("") == []

    def test_flag_tokens_preserved(self):
        tokens = split_command("uvx mcp-server-git --repository .")
        assert tokens == ["uvx", "mcp-server-git", "--repository", "."]


class TestParseEnv:
    def test_single_pair(self):
        assert _parse_env(["KEY=value"]) == {"KEY": "value"}

    def test_multiple_pairs(self):
        assert _parse_env(["A=1", "B=2"]) == {"A": "1", "B": "2"}

    def test_value_containing_equals(self):
        """Base64-ish tokens and connection strings contain '=' — only the
        first '=' splits."""
        assert _parse_env(["TOKEN=abc=def=="]) == {"TOKEN": "abc=def=="}

    def test_empty_value_allowed(self):
        assert _parse_env(["FLAG="]) == {"FLAG": ""}

    def test_missing_equals_raises(self):
        with pytest.raises(ValueError):
            _parse_env(["NOT_A_PAIR"])


class TestParseHeaders:
    def test_single_header(self):
        assert _parse_headers(["Authorization: Bearer abc"]) == {"Authorization": "Bearer abc"}

    def test_no_space_after_colon(self):
        assert _parse_headers(["X-Api-Key:secret"]) == {"X-Api-Key": "secret"}

    def test_value_containing_colons(self):
        """Header values contain colons routinely (URLs, base64 with padding)."""
        assert _parse_headers(["X-Callback: https://example.com:8443/hook"]) == {
            "X-Callback": "https://example.com:8443/hook"
        }

    def test_multiple_headers(self):
        parsed = _parse_headers(["Authorization: Bearer t", "X-Tenant: acme"])
        assert parsed == {"Authorization": "Bearer t", "X-Tenant": "acme"}

    def test_missing_colon_raises(self):
        with pytest.raises(ValueError):
            _parse_headers(["NotAHeader"])

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            _parse_headers([": value-with-no-name"])


class TestUnwrapExceptionGroup:
    def test_unwraps_nested_single_child_groups(self):
        leaf = TimeoutError("inner")
        wrapped = BaseExceptionGroup("outer", [BaseExceptionGroup("mid", [leaf])])
        assert _unwrap_exception_group(wrapped) is leaf

    def test_multi_child_group_not_descended(self):
        """A group with 2+ children is genuinely multiple failures — must be
        returned as-is, not arbitrarily collapsed to one child."""
        group = BaseExceptionGroup("outer", [ValueError("a"), KeyError("b")])
        assert _unwrap_exception_group(group) is group

    def test_plain_exception_passthrough(self):
        exc = RuntimeError("plain")
        assert _unwrap_exception_group(exc) is exc
