# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later

"""
tests/run_test_matrix.py

Automated driver for the MCP-Rubriq test matrix (tests/test_matrix.json).

For each case it invokes the real MCP-Rubriq pipeline entry point
(plugins/mcp-rubriq/skills/mcp-rubriq/scripts/lint.py) exactly as SKILL.md would,
exactly as a human would from the command line — no shortcuts through
internal functions —
so a pass here means the actual CLI surface works, not just the library code
underneath it.

Network cases (transport: sse/http) additionally spin up the matching
fixture server as a background process for the duration of the case.

Usage:
  python tests/run_test_matrix.py                     # run all non-skipped cases
  python tests/run_test_matrix.py --only TM-002        # run one case by id
  python tests/run_test_matrix.py --only custom-stdio  # substring match on id/category
  python tests/run_test_matrix.py --include-skipped    # also run cases with a skip_reason
  python tests/run_test_matrix.py --report path.md     # write the report elsewhere

Exit code is 0 only if every case that ran matched its expected outcome and
every assertion passed.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).parent.parent
LINT_SCRIPT = REPO_ROOT / "plugins" / "mcp-rubriq" / "skills" / "mcp-rubriq" / "scripts" / "lint.py"
DEFAULT_MATRIX = REPO_ROOT / "tests" / "test_matrix.json"
DEFAULT_REPORT = REPO_ROOT / "tests" / "test-matrix-results.md"


# ---------------------------------------------------------------------------
# Assertion evaluation
# ---------------------------------------------------------------------------


def _resolve_path(obj: Any, path: str) -> Any:
    """Resolve a dotted path like 'tools.0.annotations.schema_empty' against
    a JSON-decoded dict/list structure. Numeric segments index into lists."""
    current = obj
    for segment in path.split("."):
        if isinstance(current, list):
            current = current[int(segment)]
        else:
            current = current[segment]
    return current


def _check_assertion(parsed: Any, assertion: dict) -> tuple[bool, str]:
    path = assertion["path"]
    try:
        actual = _resolve_path(parsed, path)
    except (KeyError, IndexError, TypeError) as exc:
        return False, f"{path}: could not resolve ({exc})"

    if "eq" in assertion:
        expected = assertion["eq"]
        ok = actual == expected
        return ok, f"{path} == {expected!r} (actual: {actual!r})"
    if "len_gte" in assertion:
        expected = assertion["len_gte"]
        ok = isinstance(actual, list) and len(actual) >= expected
        actual_len = len(actual) if isinstance(actual, list) else "n/a"
        return ok, f"len({path}) >= {expected} (actual len: {actual_len})"
    if "contains" in assertion:
        expected = assertion["contains"]
        ok = isinstance(actual, str) and expected in actual
        return ok, f"{path} contains {expected!r} (actual: {actual!r})"
    return False, f"{path}: assertion has no recognized comparator"


# ---------------------------------------------------------------------------
# Outcome classification
# ---------------------------------------------------------------------------


def _extract_trailing_json(text: str) -> Any | None:
    """Find the JSON value at the END of text, tolerating arbitrary noise
    before it (e.g. the SDK's own logger writing a parse-failure traceback
    to stderr ahead of our own error JSON). Tries progressively longer
    suffixes from the last line backward and returns on the first (smallest,
    i.e. most specific) one that parses."""
    lines = text.strip().splitlines()
    for start in range(len(lines) - 1, -1, -1):
        candidate = "\n".join(lines[start:])
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _classify(stdout: str, stderr: str) -> tuple[str, dict | None, str]:
    """
    Returns (outcome, parsed_json_or_None, note).
    outcome is "success" or "failure".

    Both stdout and stderr are checked since lint.py's success path prints
    to stdout while its except-block prints to stderr.
    """
    for stream_name, stream in (("stdout", stdout), ("stderr", stderr)):
        text = stream.strip()
        if not text:
            continue
        parsed = _extract_trailing_json(text)
        if parsed is None:
            continue
        if isinstance(parsed, dict) and "error" in parsed:
            return "failure", parsed, f"error JSON on {stream_name}: {parsed.get('error')}"
        if stream_name == "stdout":
            return "success", parsed, "parsed OK"
    return "failure", None, "neither stream produced parseable JSON (raw crash / traceback / hang)"


# ---------------------------------------------------------------------------
# Case runners
# ---------------------------------------------------------------------------


def _subprocess_env() -> dict:
    """Env for every subprocess this runner spawns (lint.py itself, and any
    fixture server lint.py in turn spawns via a literal interpreter name like
    "python"/"python3"/"py"). Prepending sys.executable's own directory to PATH
    guarantees a literal interpreter name resolves to THIS interpreter — the one
    with mcp/pydantic/anyio/httpx installed — regardless of whether the caller
    (make matrix / tasks.ps1 / a bare `.venv/Scripts/python.exe ...` invocation)
    actually activated the venv first. Without this, a literal "python" command
    resolves via the ambient PATH, which may point at an unrelated system Python
    that lacks mcp entirely — a silent, near-total false-failure cascade that has
    nothing to do with MCP-Rubriq itself (confirmed live: this is exactly what
    happened before this fix, and it's why `make matrix`/`tasks.ps1 matrix` must
    not be trusted to "just work" without it)."""
    env = {**os.environ}
    venv_bin = str(Path(sys.executable).parent)
    env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
    return env


def _run_stdio_case(case: dict) -> tuple[str, str, float]:
    cmd = [
        sys.executable,
        str(LINT_SCRIPT),
        "--transport",
        "stdio",
        "--command",
        case["command"],
        "--timeout",
        str(case["timeout"]),
    ]
    # NOTE: these must be forwarded via --env, not just set in this process's
    # own environment — the child server only inherits the SDK's curated safe
    # allowlist plus whatever --env passes explicitly. Setting them only in
    # os.environ here silently no-ops.
    for key, value in case.get("env", {}).items():
        cmd += ["--env", f"{key}={value}"]
    if case.get("cwd"):
        cmd += ["--cwd", str(REPO_ROOT / case["cwd"])]
    # --args must be last: it's argparse.REMAINDER, so anything after it
    # (including another flag) gets swallowed into the args list.
    if case.get("args"):
        cmd += ["--args", *case["args"]]
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=_subprocess_env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=case["subprocess_timeout"],
        )
        return proc.stdout, proc.stderr, time.monotonic() - start
    except subprocess.TimeoutExpired as exc:

        def _s(v):  # TimeoutExpired yields bytes|str|None depending on platform
            if v is None:
                return ""
            return v.decode("utf-8", errors="replace") if isinstance(v, bytes) else v

        return (
            _s(exc.stdout),
            _s(exc.stderr) + "\n[runner] subprocess_timeout exceeded — likely a real hang",
            time.monotonic() - start,
        )


def _run_network_case(case: dict) -> tuple[str, str, float]:
    port = case["port"]
    fixture_env = {
        **_subprocess_env(),
        **case.get("fixture_env", {}),
        "MCP_RUBRIQ_FIXTURE_PORT": str(port),
    }
    fixture_proc = subprocess.Popen(
        case["fixture_command"],
        cwd=str(REPO_ROOT),
        env=fixture_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(case["startup_wait"])
        url = case["url_template"].format(port=port)
        cmd = [
            sys.executable,
            str(LINT_SCRIPT),
            "--transport",
            case["transport"],
            "--url",
            url,
            "--timeout",
            str(case["timeout"]),
        ]
        for header in case.get("headers", []):
            cmd += ["--header", header]
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=case["subprocess_timeout"],
            )
            return proc.stdout, proc.stderr, time.monotonic() - start
        except subprocess.TimeoutExpired as exc:
            # subprocess.run was called with text=True/encoding="utf-8" above, so
            # exc.stdout/.stderr are actually str at runtime — the TimeoutExpired
            # stub types them as bytes|None regardless of call-site text mode.
            return (
                (cast(str | None, exc.stdout) or ""),
                (cast(str | None, exc.stderr) or ""),
                time.monotonic() - start,
            )
    finally:
        fixture_proc.terminate()
        try:
            fixture_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            fixture_proc.kill()


def run_case(case: dict) -> dict:
    if case["transport"] == "stdio":
        stdout, stderr, elapsed = _run_stdio_case(case)
    else:
        stdout, stderr, elapsed = _run_network_case(case)

    outcome, parsed, note = _classify(stdout, stderr)
    expected = case["expect_outcome"]
    outcome_ok = outcome == expected

    assertion_results = []
    declared_assertions = case.get("assertions", [])
    if declared_assertions:
        if outcome_ok and parsed is not None:
            for assertion in declared_assertions:
                ok, detail = _check_assertion(parsed, assertion)
                assertion_results.append(
                    {"ok": ok, "detail": detail, "note": assertion.get("note")}
                )
        else:
            # Declared assertions with nothing to check them against must
            # fail loudly, not vacuously pass via an empty assertion list.
            reason = "outcome mismatch" if not outcome_ok else "no parseable JSON to assert against"
            assertion_results.append(
                {
                    "ok": False,
                    "detail": f"{len(declared_assertions)} assertion(s) not evaluated: {reason}",
                    "note": None,
                }
            )

    case_pass = outcome_ok and all(a["ok"] for a in assertion_results)

    return {
        "id": case["id"],
        "category": case["category"],
        "description": case["description"],
        "expected_outcome": expected,
        "actual_outcome": outcome,
        "outcome_note": note,
        "elapsed_seconds": round(elapsed, 2),
        "stdout_bytes": len(stdout.encode("utf-8", errors="replace")),
        "assertion_results": assertion_results,
        # Set on cases with a documented, confirmed non-MCP-Rubriq root cause (client
        # IT policy, upstream package incompatibility, etc.) — still run every time
        # (unlike skip_reason) so a future flip to PASS is noticed, but rendered
        # distinctly in the report so it doesn't read as an unexplained regression.
        "known_issue": case.get("known_issue"),
        "pass": case_pass,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def render_report(results: list[dict], skipped: list[dict]) -> str:
    lines = ["# Test Matrix Results", ""]
    passed = sum(1 for r in results if r["pass"])
    lines.append(f"**{passed}/{len(results)} cases passed** ({len(skipped)} skipped)")
    lines.append("")
    lines.append(
        "| ID | Category | Expected | Actual | Assertions | Time (s) | Output (KB) | Result |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        assertion_summary = (
            f"{sum(1 for a in r['assertion_results'] if a['ok'])}/{len(r['assertion_results'])}"
            if r["assertion_results"]
            else "-"
        )
        if r["pass"]:
            result_cell = "PASS"
        elif r.get("known_issue"):
            result_cell = f"FAIL (known: {r['known_issue']})"
        else:
            result_cell = "FAIL"
        stdout_kb = round(r["stdout_bytes"] / 1024, 1)
        lines.append(
            f"| {r['id']} | {r['category']} | {r['expected_outcome']} | {r['actual_outcome']} | "
            f"{assertion_summary} | {r['elapsed_seconds']} | {stdout_kb} | {result_cell} |"
        )
    lines.append("")

    failures = [r for r in results if not r["pass"]]
    if failures:
        lines.append("## Failures")
        for r in failures:
            lines.append(f"### {r['id']} — {r['description']}")
            lines.append(
                f"- Expected outcome: `{r['expected_outcome']}`, "
                f"actual: `{r['actual_outcome']}` ({r['outcome_note']})"
            )
            for a in r["assertion_results"]:
                if not a["ok"]:
                    lines.append(
                        f"- Assertion failed: {a['detail']}"
                        + (f" — {a['note']}" if a["note"] else "")
                    )
            lines.append("")

    if skipped:
        lines.append("## Skipped")
        for s in skipped:
            lines.append(f"- **{s['id']}** ({s['category']}): {s['skip_reason']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    # Same Windows cp1252 pitfall the pipeline itself had (P1-ENC): case
    # descriptions contain arrows/em-dashes that a cp1252 console can't
    # encode — the runner must not die printing its own progress lines.
    for stream in (sys.stdout, sys.stderr):
        # isinstance, not hasattr: a replaced/captured stream is typically not
        # a real io.TextIOWrapper and correctly skips this — isinstance also
        # lets pyright narrow the type, unlike hasattr.
        if isinstance(stream, io.TextIOWrapper):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument(
        "--only", type=str, default=None, help="Substring match against case id or category."
    )
    parser.add_argument("--include-skipped", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    cases = matrix["cases"]

    if args.only:
        cases = [c for c in cases if args.only in c["id"] or args.only in c["category"]]

    to_run, skipped = [], []
    for case in cases:
        if case.get("skip_reason") and not args.include_skipped:
            skipped.append(case)
        else:
            to_run.append(case)

    results = []
    for case in to_run:
        print(f"[{case['id']}] {case['description'][:80]} ...", flush=True)
        result = run_case(case)
        results.append(result)
        if result["pass"]:
            status = "PASS"
        elif result.get("known_issue"):
            status = f"FAIL (known: {result['known_issue']})"
        else:
            status = "FAIL"
        print(f"  -> {status} ({result['actual_outcome']}, {result['elapsed_seconds']}s)")

    report = render_report(results, skipped)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(f"\nReport written to {args.report}")

    all_passed = all(r["pass"] for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
