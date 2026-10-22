# MCP-Rubriq

Grade any MCP server against a published 28-rule rubric, before an agent has to use it.
MCP-Rubriq connects to a Model Context Protocol server, reads how every tool, resource and
prompt describes itself, and scores that against an explicit rubric. You get a report with a
severity per finding, the exact evidence from the server's own metadata, and a concrete fix,
plus the rules that passed and the rules that did not apply.

Point it at a server you are building, one you are about to depend on, or one already running.

## Install

```text
/plugin marketplace add trackmind-ai/marketplace
/plugin install mcp-rubriq@trackmind
```

Then ask Claude to run it:

```text
/mcp-rubriq test my server
/mcp-rubriq python my_server.py
/mcp-rubriq http://localhost:8000/mcp
```

## The rubric

The 28 rules live in `skills/mcp-rubriq/rulebook/rules/`, one Markdown file each, with a
stated rationale, explicit pass criteria, explicit fail criteria and an evidence requirement.
They fall into five groups: tool quality (T), input schemas (S), resources and prompts (R),
agent ergonomics (A) and security (X), including undocumented destructive actions, credential
exposure, command injection, prompt injection in metadata and cross-server tool shadowing.

## How it works

1. A structural step connects to the server and reads its tools, resources and prompts.
2. A deterministic annotator computes facts about them: counts, naming conventions,
   missing descriptions, schema gaps and keyword signals.
3. Claude acts as the judge. It reads the relevant rule files and grades the annotated
   server against them. The judge is Claude itself in your conversation; no separate model
   or API is called.

## What this plugin runs, sends and fetches

Nothing here is hidden. This is the complete list.

**It starts the server you point it at.** To read a server's metadata it must launch or
connect to it:

- For a command you give (`python my_server.py`, `npx -y some-server`), it **runs that
  command on your machine** with your permissions. `npx -y <package>` downloads and runs
  that package from npm. Only point it at servers you are willing to run.
- For a published server named in `skills/mcp-rubriq/introspection/known_servers.json`
  (11 entries), it uses the launch command recorded there, which is `npx -y` or
  `uvx` with the official package pinned to an exact version. If a name is not in that list, Claude may suggest a
  command from its own knowledge and tells you it is unverified before running it.
- For an HTTP or SSE URL, it connects to that URL and sends the request headers you
  supply (for example `Authorization`).
- It can pass environment variables you give it (for example `GITHUB_TOKEN`) to the server
  it launches. It asks you for values and never invents them. You can export the value in
  your shell and reference it by name so the secret never appears in the conversation.

**Its own code.** A Python script (`scripts/lint.py`) runs through `uv run`. `uv` resolves
exact-pinned dependencies into an ephemeral environment on first use: `mcp==1.30.0`,
`pydantic==2.14.1`, `anyio==4.15.1`, `httpx==0.28.1` (plus `exceptiongroup==1.3.1` on Python
below 3.11), downloaded from PyPI. Without `uv`, the fallback is `pip install -r
skills/mcp-rubriq/introspection/requirements.txt`, which holds the same pins.

**No hooks, no MCP servers of its own, no background processes, no telemetry.** It does not
modify Claude settings. It does not search your file system: a name that only resembles a
file is never a reason to search; it asks you instead.

**What leaves your machine.** Only what the server you chose receives (the connection,
headers and environment above). The server's metadata is read into your Claude conversation
for grading. The plugin sends nothing to Trackmind or any other service.

**Files it writes.** None in your project unless you ask it to save the report.

## Try it

Three prompts to start with:

1. `/mcp-rubriq test my server`. Finds the MCP server project in your current folder, launches
   it, and grades it.
2. `/mcp-rubriq http://localhost:8000/mcp`. Grades a server that is already running.
3. `/mcp-rubriq filesystem`. Grades a well-known published server by name. Claude asks which
   directory to give it.

Each run ends with a report: severity per finding, the evidence from the server's own
metadata, a fix, and the rules that passed or did not apply.

## Troubleshooting

- **The run times out.** A cold `npx` or `uvx` start can take longer than the default 30
  seconds. Ask Claude to re-run with a longer `--timeout`.
- **`401 Unauthorized` from a hosted server.** The server needs credentials. Ask Claude to
  re-run with an `Authorization` header. Export the token in your shell and have Claude
  reference it by name so the token stays out of the conversation.
- **A server needs environment variables.** Claude asks for them and never invents values.
  Pass only the ones that server documents.
- **The interpreter is blocked or packages are missing.** On machines with application
  control, a launcher can be blocked. Claude falls back to a Python interpreter that already
  has the packages, or stops and reports the exact error.

## Requirements

Claude Code, plus `uv` (or Python 3.10+ with `pip`). Node.js only if the server you test is
launched with `npx`.

## Documentation, support and license

Rule reference, architecture, testing and boundaries are in the
[repository](https://github.com/trackmind-ai/mcp-rubriq) (`docs/`). Report problems, false
positives and rule proposals at <https://github.com/trackmind-ai/mcp-rubriq/issues>.
Licensed under the GNU General Public License, version 3 or later (see the repository `LICENSE`).
Versions up to 0.1.2 were released under the MIT License.
