# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- Plugin README: added three example prompts and a troubleshooting section.
- License changed from MIT to GPL-3.0-or-later for new versions. `LICENSE` is now the GNU GPL v3 text, the SPDX headers, `plugin.json` and the README say so, and `CONTRIBUTING.md` states that contributions are licensed under it. Versions up to 0.1.2 stay available under MIT.

## [0.1.2] — 2026-10-21

### Changed
- Every launcher in `known_servers.json` is pinned to an exact version (`npx pkg@x.y.z`, `uvx pkg==x.y.z`) instead of running whatever is latest, and `tests/test_known_servers.py` keeps it that way. github, brave-search, puppeteer and slack are deprecated on npm and sqlite is archived; they stay listed and the file now says so.

### Fixed
- The `filesystem` registry entry launched the server with no allowed directory, so it advertised 0 tools (14 with one) and graded as an empty server. It now carries a `<path>` placeholder with a note, and the skill substitutes `<path>` before running.

## [0.1.1] — 2026-10-19

Directory-submission readiness.

### Added
- `plugins/mcp-rubriq/README.md` with a full disclosure of what the plugin runs, sends and fetches.

### Fixed
- A JSON Schema `type` given as a list (for example `["boolean", "string"]` or `["integer", "null"]`) crashed the whole run with a pydantic `ValidationError`. The official `@modelcontextprotocol/server-sequential-thinking` server hit this. The model now accepts the list form, and the annotator treats `["integer", "null"]` as an integer (bounds check) and a multi-type union as typed rather than missing.

### Changed
- Runtime dependencies are pinned to exact versions in both `scripts/lint.py` (PEP 723 block, with `exclude-newer`) and `introspection/requirements.txt`.

## [0.1.0] — 2026-08-13

Initial public release.

### Added

- **The rubric** — 28 rules across five categories, each a markdown file under
  `rulebook/rules/` carrying its own rationale, explicit pass criteria, explicit fail criteria,
  and an evidence requirement. Tool Quality (7), Schema Integrity (7), Architecture (5),
  Resource & Prompt Quality (3), Security Signals (6). Severity tracks quality impact rather
  than MCP spec conformance; rules that do encode a real spec requirement say so.
- **Three-stage pipeline** — introspect (connect and list what the server declares) → annotate
  (a fast, deterministic high-recall pass computing facts, not verdicts) → judge (an LLM applies
  the rubric's written criteria against the actual content). The split keeps heuristics from
  over-flagging and stops the judge re-deriving mechanical facts on every run.
- **The `/mcp-rubriq` command**, resolving a target from a launch command, an HTTP/SSE URL, a
  local unpublished project, or the name of a well-known server.
- **Transports** — `stdio`, SSE, and streamable HTTP. `--env` passes environment variables to a
  stdio-launched server; `--header` sets a static auth header for HTTP and SSE. Neither requires
  typing a secret into the conversation.
- **A registry of well-known servers** resolvable by name: `filesystem`, `fetch`, `everything`,
  `git`, `memory`, `sqlite`, `github`, `brave-search`, `puppeteer`, `slack`.
- **Hardening against hostile and broken targets.** A server that crashes mid-session, returns
  garbage, hangs, advertises a capability it doesn't implement, or embeds prompt-injection
  payloads in its metadata degrades to a specific error or an explicitly partial result — never
  a silently wrong one. Target metadata is treated as untrusted content throughout; the judge
  cites injection attempts as evidence rather than complying with them.
- **Tests** — 131 unit tests covering the annotator's heuristics, schema resolution
  (`$ref`/`oneOf`/`allOf`, cyclic references, depth guards), and CLI parsing and error paths;
  plus a 48-case integration matrix driving the real CLI entry point as a subprocess, of which
  44 run and pass and 4 are skipped by design (3 need real API credentials, 1 downloads a
  Chromium build on first run).
- **Documentation** — `README.md`, `CONTRIBUTING.md` (a three-lane contribution model),
  `SECURITY.md`, `CODE_OF_CONDUCT.md`, `LICENSE` (MIT), and `docs/` covering the architecture,
  the rule reference, what is deliberately out of scope, and how to run the tests.
- **Installation** — one-command installers for macOS/Linux and Windows, plus the plain
  `/plugin` commands for anyone who would rather not run a script. MCP-Rubriq is published
  through the shared [`trackmind-ai/marketplace`](https://github.com/trackmind-ai/marketplace)
  catalog:

  ```
  /plugin marketplace add trackmind-ai/marketplace
  /plugin install mcp-rubriq@trackmind
  ```

### Known limitations

MCP-Rubriq grades declared metadata only. It never calls a tool, so it cannot tell you whether
one is actually fast, genuinely idempotent, or behaves the way it claims. It also does not audit
auth or transport security, and cannot detect a server changing its definitions after a client
approved them. These are architectural boundaries, not gaps — `docs/boundaries.md` has the
complete reasoned list.

[0.1.0]: https://github.com/trackmind-ai/mcp-rubriq/releases/tag/v0.1.0
