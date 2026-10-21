# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/test_known_servers.py

known_servers.json is the deterministic launch registry the skill runs for a named server
(`npx -y <pkg>`, `uvx <pkg>`). Every launcher must be pinned to an exact version so the
plugin never runs whatever happens to be latest, and every `<path>` placeholder must be
documented so the skill knows to substitute it.
"""

import json
import re
from pathlib import Path

import pytest

REGISTRY = (
    Path(__file__).resolve().parent.parent
    / "plugins/mcp-rubriq/skills/mcp-rubriq/introspection/known_servers.json"
)
ENTRIES = {
    k: v
    for k, v in json.loads(REGISTRY.read_text(encoding="utf-8")).items()
    if not k.startswith("_")
}

NPX_PIN = re.compile(r"^(@[\w.-]+/)?[\w.-]+@\d[\w.+-]*$")  # pkg@1.2.3 or @scope/pkg@1.2.3
UVX_PIN = re.compile(r"^[\w.-]+==\d[\w.+-]*$")  # pkg==1.2.3


def _package_arg(entry: dict) -> str:
    args = [a for a in entry["args"] if a != "-y"]
    return args[0]


@pytest.mark.parametrize("name", sorted(ENTRIES))
def test_launcher_is_pinned_to_an_exact_version(name: str) -> None:
    entry = ENTRIES[name]
    pkg = _package_arg(entry)
    if entry["command"] == "npx":
        assert "-y" in entry["args"], f"{name}: npx launcher should pass -y"
        assert NPX_PIN.match(pkg), f"{name}: '{pkg}' is not pinned (expected pkg@x.y.z)"
    elif entry["command"] == "uvx":
        assert UVX_PIN.match(pkg), f"{name}: '{pkg}' is not pinned (expected pkg==x.y.z)"
    else:
        pytest.fail(f"{name}: unexpected launcher command {entry['command']!r}")


@pytest.mark.parametrize("name", sorted(ENTRIES))
def test_no_floating_version_tags(name: str) -> None:
    joined = " ".join(ENTRIES[name]["args"])
    assert "@latest" not in joined and "@next" not in joined


@pytest.mark.parametrize("name", sorted(ENTRIES))
def test_path_placeholders_are_documented(name: str) -> None:
    entry = ENTRIES[name]
    if "<path>" in entry["args"]:
        assert "<path>" in entry.get("_note", ""), f"{name}: <path> placeholder has no _note"


def test_filesystem_gets_an_allowed_directory() -> None:
    # Launched with no directory the server advertises 0 tools and would grade as empty.
    assert "<path>" in ENTRIES["filesystem"]["args"]
