# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT
#
# MCP-Rubriq — dev tasks (Mac/Linux/CI). Windows/PowerShell: use tasks.ps1 instead.
#
# `make setup` bootstraps a local .venv; every other target below uses that
# venv's binaries explicitly, so they work whether or not you've personally
# `source .venv/bin/activate`d in your current shell.
#
# Every tool is invoked as `python -m <tool>` rather than calling its own
# binary directly. Confirmed empirically on Windows (not just in theory)
# this matters: a machine-level Application Control policy blocked `pip`
# directly while `python -m pip` succeeded immediately after — harmless
# elsewhere, so kept consistent on every platform. One exception: ruff's
# Python wrapper still subprocess-spawns the compiled ruff binary
# underneath either way, so `python -m ruff` doesn't dodge that specific
# class of block the way it does for pip/pytest/pyright — noted here in
# case it resurfaces.

VENV := .venv
BIN  := $(VENV)/bin
PY   := $(BIN)/python

.PHONY: setup test matrix lint format typecheck validate load check clean

setup:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"
	$(PY) -m pip install -r plugins/mcp-rubriq/skills/mcp-rubriq/introspection/requirements.txt
	@echo ""
	@echo "Setup complete. Every other 'make' target below uses $(VENV) automatically."
	@echo "For an interactive shell in it: source $(VENV)/bin/activate"

test:
	$(PY) -m pytest -q

matrix:
	$(PY) tests/run_test_matrix.py

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format:
	$(PY) -m ruff format .

typecheck:
	$(PY) -m pyright

# Validates both manifests: marketplace.json (repo root) and plugin.json
# (plugins/mcp-rubriq/.claude-plugin/), via one recursive check from the root.
validate:
	claude plugin validate .

# Local dogfood install — registers this checkout as the `trackmind-dev`
# marketplace and installs MCP-Rubriq from it, both at --scope local so it never
# touches your user-wide Claude Code config. Safe to re-run.
#
# `trackmind-dev` is deliberately NOT the published marketplace name (`trackmind`,
# served from trackmind-ai/marketplace). Claude Code keeps one marketplace per
# name, so sharing the name would make this checkout silently replace the
# published catalog on your own machine.
load:
	-claude plugin marketplace add ./ --scope local
	claude plugin install mcp-rubriq@trackmind-dev --scope local

# The "before you push" target.
check: lint typecheck test
	@echo "All checks passed."

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache
