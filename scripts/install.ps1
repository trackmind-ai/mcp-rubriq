# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later
#
# One-command installer for MCP-Rubriq (Windows / PowerShell).
#
#   irm https://raw.githubusercontent.com/trackmind-ai/mcp-rubriq/main/scripts/install.ps1 | iex
#
# What this does, in order:
#   1. Confirms the `claude` CLI is present (the one prerequisite that can't
#      be automated away -- there's nothing to install a plugin into without it).
#   2. Installs `uv` if it's missing, via Astral's official installer.
#      Announces this before doing it -- nothing happens silently.
#   3. Registers the trackmind marketplace and installs MCP-Rubriq from it, both
#      via the non-interactive `claude plugin ...` CLI subcommands. Verified
#      directly (not assumed) that these show no confirmation prompt -- that
#      dialog only appears in the interactive `/plugin install` slash command,
#      which this script never touches.
#   4. Prints a one-line command you can run to confirm it worked. Deliberately
#      NOT run automatically: it invokes the LLM judge, which spends real API
#      tokens, and an install script shouldn't spend your money without you
#      explicitly asking it to.
#
# Safe to re-run: each step tolerates "already there" and moves on.

$ErrorActionPreference = "Stop"

$MarketplaceSource = "trackmind-ai/marketplace"
$MarketplaceName   = "trackmind"
$PluginSpec        = "mcp-rubriq@trackmind"

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Info($msg) { Write-Host "  $msg" }
function Fail($msg) { Write-Host "`nERROR: $msg" -ForegroundColor Red; exit 1 }

Step "Checking for the Claude Code CLI"
$claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claudeCmd) {
    Fail "'claude' was not found on PATH. Install Claude Code first: https://code.claude.com/docs/en/quickstart -- then re-run this script."
}
Info "found: $($claudeCmd.Source)"

Step "Checking for uv (resolves MCP-Rubriq's Python dependencies automatically)"
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCmd) {
    Info "found: $($uvCmd.Source)"
} else {
    Info "not found -- installing uv via the official installer (astral.sh/uv):"
    Info "  powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uvCmd) {
        Write-Host "`nuv was installed but is not on PATH in this session."
        Write-Host "Open a new terminal before using MCP-Rubriq."
    }
}

Step "Registering the trackmind marketplace"
# The `owner/repo` shorthand clones over SSH by default, which fails on any
# machine that hasn't already trusted GitHub's SSH host key (confirmed live:
# a clean-ish machine with no prior `ssh -T git@github.com` gets a hard
# "Host key verification failed" here). Most people installing a Claude Code
# plugin won't have SSH configured for GitHub, so force HTTPS instead.
$env:CLAUDE_CODE_PLUGIN_PREFER_HTTPS = "1"
try {
    claude plugin marketplace add $MarketplaceSource --scope user
    Info "marketplace registered"
} catch {
    Info "marketplace add reported an issue above -- if it's already registered, this is safe to ignore; otherwise re-run this script."
}

Step "Installing MCP-Rubriq"
try {
    claude plugin install $PluginSpec --scope user
    Info "MCP-Rubriq installed"
} catch {
    Fail "plugin install failed -- see the message above. Try: claude plugin marketplace update $MarketplaceName, then re-run this script."
}

Step "Done"
Info "Verify it works (this grades a server against the rubric and spends a small amount of API"
Info "usage, so it's left for you to run rather than done automatically):"
Write-Host "`n  /mcp-rubriq test my server`n"
Info "or, from a terminal, non-interactively:"
Write-Host "`n  claude -p `"/mcp-rubriq:mcp-rubriq python path/to/your_server.py`"`n"
