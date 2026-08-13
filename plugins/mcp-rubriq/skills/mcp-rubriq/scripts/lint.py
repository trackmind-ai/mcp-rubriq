# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.0.0,<2.0.0",
#     "pydantic>=2.0.0,<3.0.0",
#     "anyio>=4.0.0,<5.0.0",
#     "httpx>=0.27.0",
#     "exceptiongroup>=1.0.0; python_version<'3.11'",
# ]
# ///

"""
scripts/lint.py

Runs the full MCP-Rubriq pipeline up to the LLM Judge step.
1. Runs introspection to connect to the server and get the raw ServerModel.
2. Runs the Annotator to produce the AnnotatedServerModel.
3. Outputs the AnnotatedServerModel as JSON to stdout.

Invoked via `uv run` (see SKILL.md Step 2): the PEP 723 block above lets uv
resolve mcp/pydantic/anyio into an ephemeral environment on first use, with
no manual `pip install` step for the end user. `uv run` still executes this
same file directly, so the sys.path bootstrap below (for the sibling
introspection/models/rulebook packages, which are local, not PyPI deps) is
unaffected — it's a separate concern PEP 723 doesn't touch.
"""

import argparse
import asyncio
import io
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# These imports must come after the sys.path.insert above (that's what makes the
# top-level `introspection`/`rulebook` packages resolvable) — the E402 the linter would
# otherwise raise here is expected, not a mistake.
from introspection.introspect import (  # noqa: E402
    _parse_env,
    _parse_headers,
    introspect_http,
    introspect_sse,
    introspect_stdio,
    split_command,
)
from rulebook.annotator import annotate  # noqa: E402


def _force_utf8_stdio() -> None:
    """On Windows, this process's OWN stdout/stderr default to the locale
    code page (e.g. cp1252) when piped — so printing a model that contains
    CJK/emoji metadata dies with UnicodeEncodeError even after the child
    server's encoding is fixed (found live: tests/fixtures/unicode_server.py).
    Force UTF-8 on both streams; guard with isinstance because a
    replaced/captured stream (pytest, wrappers) is typically not a real
    io.TextIOWrapper and correctly skips this — isinstance also lets pyright
    narrow the type, unlike hasattr."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


async def main():
    _force_utf8_stdio()
    parser = argparse.ArgumentParser(description="MCP-Rubriq Introspection and Annotation")
    parser.add_argument("--transport", choices=["stdio", "sse", "http"], required=True)
    parser.add_argument("--command", type=str, help="Command to run for stdio transport")
    parser.add_argument(
        "--args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Extra arguments to pass to --command, as separate tokens (stdio only). "
        "Prefer this over embedding a path in --command when the path contains "
        "a space — an unquoted space in --command is ambiguous and cannot be "
        "split correctly; see split_command(). "
        "MUST be the last flag on the command line — it consumes every remaining "
        "token literally (including ones starting with '-', like npx's -y), so "
        "anything after it (--env, --timeout) would otherwise be silently "
        "swallowed into this list instead of being parsed as its own flag.",
    )
    parser.add_argument("--url", type=str, help="URL for sse/http transport")
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        metavar="NAME: VALUE",
        help="HTTP header to send when connecting (sse/http only). Repeatable. "
        'Example: --header "Authorization: Bearer $TOKEN". Required for '
        "auth-protected hosted servers.",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Environment variable to pass to a stdio server. Repeatable.",
    )
    parser.add_argument(
        "--cwd",
        type=str,
        default=None,
        help="Working directory to launch the stdio server in (stdio only). "
        "Pass the server's resolved absolute folder path whenever --command/--args "
        "reference it by a relative path — otherwise the child process launches "
        "wherever this script itself happened to be invoked from, not the server's "
        "own directory.",
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="Operation timeout in seconds (default: 30)."
    )

    args = parser.parse_args()

    try:
        # Step 1: Introspect
        if args.transport == "stdio":
            if not args.command:
                print('{"error": "Must provide --command for stdio transport"}', file=sys.stderr)
                sys.exit(1)
            if args.args:
                cmd = args.command
                extra_args = args.args
            else:
                parts = split_command(args.command)
                cmd = parts[0]
                extra_args = parts[1:]
            env = _parse_env(args.env) if args.env else None
            raw_model = await introspect_stdio(cmd, extra_args, args.timeout, env, args.cwd)
        elif args.transport == "sse":
            if not args.url:
                print('{"error": "Must provide --url for sse transport"}', file=sys.stderr)
                sys.exit(1)
            headers = _parse_headers(args.header) if args.header else None
            raw_model = await introspect_sse(args.url, args.timeout, headers)
        else:
            if not args.url:
                print('{"error": "Must provide --url for http transport"}', file=sys.stderr)
                sys.exit(1)
            headers = _parse_headers(args.header) if args.header else None
            raw_model = await introspect_http(args.url, args.timeout, headers)

        # Step 2: Annotate
        annotated_model = annotate(raw_model)

        # Output Annotated Model JSON to stdout
        print(annotated_model.model_dump_json(indent=2))

    except TimeoutError:
        print(
            json.dumps(
                {
                    "error": f"Connection timed out after {args.timeout}s.",
                    "detail": "Increase --timeout or verify the server is reachable.",
                }
            ),
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e), "detail": type(e).__name__}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
