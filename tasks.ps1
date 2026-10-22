# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later
#
# MCP-Rubriq — dev tasks (Windows / PowerShell). Mac/Linux/CI: use the Makefile instead.
#
# `setup` bootstraps a local .venv; every other task below uses that venv's
# binaries explicitly, so they work whether or not you've personally
# activated the venv in your current shell.
#
# Usage: .\tasks.ps1 <setup|test|matrix|lint|format|typecheck|validate|load|check|clean>

param(
    [Parameter(Position = 0)]
    [string]$Task = "help"
)

$ErrorActionPreference = "Stop"
$Venv = ".venv"
$Bin  = "$Venv\Scripts"

function Invoke-Checked {
    # Runs an external command and stops the script if it exits non-zero —
    # PowerShell does NOT do this by default for external .exe calls, unlike
    # a Makefile recipe line, so this makes task-Check's fail-fast behavior
    # actually match the Makefile's.
    param([string]$Exe, [string[]]$ExeArgs)
    & $Exe @ExeArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $Exe $($ExeArgs -join ' ')" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# Every tool below is invoked as `python -m <tool>` rather than calling its
# own .exe directly. Confirmed empirically (not just in theory) this matters
# on Windows: a machine-level Application Control policy blocked `pip.exe`
# directly while `python -m pip` succeeded immediately after. Note ruff is
# the one exception this doesn't fully fix — its Python wrapper still
# subprocess-spawns the compiled ruff binary underneath either way, so it's
# blocked by the same policy regardless of invocation style on an affected
# machine; harmless everywhere else, so kept consistent.

function Task-Setup {
    python -m venv $Venv
    & "$Bin\python.exe" -m pip install --upgrade pip
    & "$Bin\python.exe" -m pip install -e ".[dev]"
    & "$Bin\python.exe" -m pip install -r plugins/mcp-rubriq/skills/mcp-rubriq/introspection/requirements.txt
    Write-Host ""
    Write-Host "Setup complete. Every other task below uses $Venv automatically."
    Write-Host "For an interactive shell in it: $Venv\Scripts\Activate.ps1"
}

function Task-Test {
    Invoke-Checked "$Bin\python.exe" @("-m", "pytest", "-q")
}

function Task-Matrix {
    Invoke-Checked "$Bin\python.exe" @("tests/run_test_matrix.py")
}

function Task-Lint {
    Invoke-Checked "$Bin\python.exe" @("-m", "ruff", "check", ".")
    Invoke-Checked "$Bin\python.exe" @("-m", "ruff", "format", "--check", ".")
}

function Task-Format {
    & "$Bin\python.exe" -m ruff format .
}

function Task-Typecheck {
    Invoke-Checked "$Bin\python.exe" @("-m", "pyright")
}

# Validates both manifests: marketplace.json (repo root) and plugin.json
# (plugins/mcp-rubriq/.claude-plugin/), via one recursive check from the root.
function Task-Validate {
    Invoke-Checked "claude" @("plugin", "validate", ".")
}

# Local dogfood install — registers this checkout as the `trackmind-dev`
# marketplace and installs MCP-Rubriq from it, both at --scope local so it never
# touches your user-wide Claude Code config. `trackmind-dev` is deliberately NOT
# the published marketplace name (`trackmind`, served from trackmind-ai/marketplace)
# — Claude Code keeps one marketplace per name, so sharing it would make this
# checkout silently replace the published catalog on your own machine. Safe to re-run — tolerates "already
# registered" on the marketplace-add step the same way the Makefile's `-`
# prefix does (deliberately not using Invoke-Checked for that one line).
function Task-Load {
    claude plugin marketplace add ./ --scope local
    Invoke-Checked "claude" @("plugin", "install", "mcp-rubriq@trackmind-dev", "--scope", "local")
}

function Task-Check {
    Task-Lint
    Task-Typecheck
    Task-Test
    Write-Host "All checks passed."
}

function Task-Clean {
    Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force
    Remove-Item -Recurse -Force ".pytest_cache", ".ruff_cache", ".mypy_cache" -ErrorAction SilentlyContinue
}

switch ($Task) {
    "setup"     { Task-Setup }
    "test"      { Task-Test }
    "matrix"    { Task-Matrix }
    "lint"      { Task-Lint }
    "format"    { Task-Format }
    "typecheck" { Task-Typecheck }
    "validate"  { Task-Validate }
    "load"      { Task-Load }
    "check"     { Task-Check }
    "clean"     { Task-Clean }
    default {
        Write-Host "Usage: .\tasks.ps1 <setup|test|matrix|lint|format|typecheck|validate|load|check|clean>"
    }
}
