#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT
#
# One-command installer for MCP-Rubriq (macOS / Linux).
#
#   curl -fsSL https://raw.githubusercontent.com/trackmind-ai/mcp-rubriq/main/scripts/install.sh | bash
#
# What this does, in order:
#   1. Confirms the `claude` CLI is present (the one prerequisite that can't
#      be automated away — there's nothing to install a plugin into without it).
#   2. Installs `uv` if it's missing, via Astral's official installer.
#      Announces this before doing it — nothing happens silently.
#   3. Registers the trackmind marketplace and installs MCP-Rubriq from it, both
#      via the non-interactive `claude plugin ...` CLI subcommands. Verified
#      directly (not assumed) that these show no confirmation prompt — that
#      dialog only appears in the interactive `/plugin install` slash command,
#      which this script never touches.
#   4. Prints a one-line command you can run to confirm it worked. Deliberately
#      NOT run automatically: it invokes the LLM judge, which spends real API
#      tokens, and an install script shouldn't spend your money without you
#      explicitly asking it to.
#
# Safe to re-run: each step tolerates "already there" and moves on.

set -euo pipefail

MARKETPLACE_SOURCE="trackmind-ai/marketplace"
MARKETPLACE_NAME="trackmind"
PLUGIN_SPEC="mcp-rubriq@trackmind"

info()  { printf '  %s\n' "$1"; }
step()  { printf '\n==> %s\n' "$1"; }
fail()  { printf '\nERROR: %s\n' "$1" >&2; exit 1; }

step "Checking for the Claude Code CLI"
if ! command -v claude >/dev/null 2>&1; then
  fail "'claude' was not found on PATH. Install Claude Code first: https://code.claude.com/docs/en/quickstart — then re-run this script."
fi
info "found: $(command -v claude)"

step "Checking for uv (resolves MCP-Rubriq's Python dependencies automatically)"
if command -v uv >/dev/null 2>&1; then
  info "found: $(command -v uv)"
else
  info "not found — installing uv via the official installer (astral.sh/uv):"
  info "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # The installer typically places uv in ~/.local/bin, which may not be on
  # PATH yet in this shell session.
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v uv >/dev/null 2>&1; then
    printf '\nuv was installed but is not on PATH in this shell session.\n'
    printf 'Open a new terminal (or re-source your shell profile) before using MCP-Rubriq.\n'
  fi
fi

step "Registering the trackmind marketplace"
# The `owner/repo` shorthand clones over SSH by default, which fails on any
# machine that hasn't already trusted GitHub's SSH host key (confirmed live:
# a clean-ish machine with no prior `ssh -T git@github.com` gets a hard
# "Host key verification failed" here). Most people installing a Claude Code
# plugin won't have SSH configured for GitHub, so force HTTPS instead.
export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1
if claude plugin marketplace add "$MARKETPLACE_SOURCE" --scope user 2>&1; then
  info "marketplace registered"
else
  info "marketplace add reported an issue above — if it's already registered, this is safe to ignore; otherwise re-run this script."
fi

step "Installing MCP-Rubriq"
if claude plugin install "$PLUGIN_SPEC" --scope user 2>&1; then
  info "MCP-Rubriq installed"
else
  fail "plugin install failed — see the message above. Try: claude plugin marketplace update $MARKETPLACE_NAME, then re-run this script."
fi

step "Done"
info "Verify it works (this runs the linter and spends a small amount of API"
info "usage, so it's left for you to run rather than done automatically):"
printf '\n  /mcp-rubriq test my server\n\n'
info "or, from a terminal, non-interactively:"
printf '\n  claude -p "/mcp-rubriq:mcp-rubriq python path/to/your_server.py"\n\n'
