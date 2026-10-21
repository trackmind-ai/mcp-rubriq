---
name: mcp-rubriq
description: >
  Grades MCP (Model Context Protocol) servers against a 28-rule quality rubric.
  Connects to any MCP server — already running or launched on demand — introspects its
  tools, resources, and prompts, and grades them against explicit, published pass/fail criteria.
---

# MCP-Rubriq — MCP Server Quality Rubric

## What I Do
When invoked with `/mcp-rubriq <target>`, I connect to the specified MCP server, retrieve its metadata, run a high-recall structural annotator, and then grade the annotated facts against MCP-Rubriq's rubric to produce a high-precision quality report.

## How to Invoke Me
```
/mcp-rubriq <target>
```

Where `<target>` is one of:
- A shell command that launches the server, e.g. `python my_server.py` or `npx my-mcp-server`
- An HTTP/SSE URL for an already-running server, e.g. `http://localhost:8000/sse`
- A reference to a local, unpublished project you're actively building, e.g. "test my server" or "the one in this folder" — **the most common case this tool is built for**
- The name of a published server, either already connected to Claude Code or resolvable from `known_servers.json`

## Workflow

### Step 1 — Resolve the Target
MCP-Rubriq's primary use case is a **local, unpublished, often in-progress server** — pattern-match the user's phrasing against the examples below, then resolve using the matching sub-step. Never guess repeatedly and never expand into an unbounded filesystem search: if resolution is genuinely ambiguous after the bounded checks below, or the resolved command fails when actually run, **stop and ask the user one targeted question instead of trying another guess.**

**THE ONE GUARDRAIL THAT APPLIES TO ALL OF STEP 1, STATED ONCE:** a name or word in the
request that merely *resembles* a filename is never grounds for a file-system search of
any kind — no `Glob`, no `find`, no `grep -r`, no matter how narrow it looks, and no
matter which sub-step (1a/1b/1c) you're in. Each sub-step below defines its own small,
*bounded* check (a fixed lookup, a fixed list of exact paths); none of them has a
fallback to a broader search when the bounded check comes up empty — an empty result
*is* the answer, and the answer is to ask the user. The only way to skip resolution
entirely is the *first* phrasing example below: the user gave the actual, complete,
executable path or command verbatim. If they didn't, it's Step 1b (or 1a/1c) — never a
search.

**Phrasing examples:**
- *"python my_server.py"*, *"npx -y @foo/server"*, *"http://localhost:8000/mcp"* → an exact command/URL was given verbatim. Use it directly — no resolution needed, no verification search.
- *"fetch"*, *"filesystem"*, *"the everything server"* → a named published server. → **Step 1a.**
- *"test my server"*, *"the one in this folder"*, *"my local server in ./my-project"*, *"test my sample_server"*, *"lint my weather-mcp"*, *"grade my weather-mcp"*, *"review my mcp server"* → a local/unpublished project reference — **this is the common case; expect it more often than an exact command.** Any phrasing that isn't a literal, complete command/path falls here, even if it contains a word that looks like it could name a file. → **Step 1b.**
- *"the server I'm already connected to"*, *"the X server we're using right now"* → **Step 1c.**

#### Step 1a — Named published server
1. **First**, check `introspection/known_servers.json` (in this skill's own directory) for an entry with that name. If found, use its `transport`, `command`, and `args` directly — this is a verified, deterministic lookup, not a guess. If the entry lists `env` variable names and the user hasn't supplied values for them, ask for them (do not invent values) — and **offer the safer alternative**: if they've already exported the value in their own shell (e.g. `export GITHUB_TOKEN=...`), the command can reference it by name (`--env GITHUB_TOKEN=$GITHUB_TOKEN`) so the shell substitutes the real value at execution time and the literal secret never has to appear in the conversation. Don't assume this over pasting the raw value — offer it, let the user choose. If an `args` entry is the placeholder `<path>` (filesystem, git, sqlite), read the entry's `_note`, ask the user which directory or file to use (or use the project folder if they said "this folder"), and substitute it before running — never run the literal `<path>`.
2. **Only if the name isn't in the registry**, fall back to your general knowledge of official MCP servers to guess the launch command — and explicitly tell the user this command is unverified/inferred, not looked up.
3. No filesystem search here either (see the guardrail above) — a registry miss means guess-from-knowledge-and-disclose, not go looking.

#### Step 1b — Local/unpublished project reference
**How to check, mechanically:** list the target folder's own immediate contents *once* (e.g. `ls <folder>` — a single, non-recursive directory listing) — or attempt to read each of the four exact paths directly and treat "not found" as absent. A bare `Glob` pattern for these filenames (e.g. `Glob("mcp.json")`) is an unscoped, recursive search of the entire project tree by default — exactly the search the guardrail above forbids, just wearing a different disguise. If your tool supports restricting Glob to one directory, that's fine; a bare filename pattern is not.

Check, **in order, only these exact paths** relative to the folder the user named (or the current working directory if none was named):
1. `mcp.json`
2. `.mcp.json`
3. `claude_desktop_config.json`
4. a `"mcp"` key inside `package.json`

**This is one check, against one folder, done once** — never several candidate folders tried in sequence. If the user's phrasing doesn't name a folder, "the folder" is the current working directory, full stop; it is never license to then check `tests/`, `tests/fixtures/`, or any other plausible-looking subdirectory as a fallback, even if a word in the request resembles something you'd expect to find there. Widening from one location to a short sequence of likely-looking ones is still the "guess repeatedly" pattern the guardrail above forbids — it's just guessing at *folders* instead of *filenames*. As soon as the single check returns an answer, stop:
- **Exactly one** server definition found → use it directly.
- **None** found → **stop and ask the user for the exact launch command** (or the port, if already running) — immediately, having checked only the one folder above. No recursing into subdirectories, no searching parent directories, no broader `grep`/`find`/`Glob`, no inferring a command from the folder's contents, and no trying a second or third folder that merely seems plausible — the bounded check coming up empty **is** the answer.
- **Multiple** found → list them by name and ask the user which one.

**Record the target folder's absolute path** as soon as it's resolved (whether the user named it directly or it came from the current working directory) — Step 2 needs it verbatim as `--cwd`. This matters regardless of where Claude's own shell happens to be sitting: MCP-Rubriq must work the same way no matter what directory it's invoked from, as long as a path is given or resolvable. If the resolved `command`/`args` reference the server by a relative path (e.g. `python my_server.py`, the common case from `mcp.json`), that relative path only resolves correctly when the child process is launched *from the server's own directory* — not from wherever the invoking shell's current directory happens to be. Absolute commands (e.g. `npx`, a fully-qualified script path) don't strictly need it, but passing `--cwd` costs nothing and is safe to include regardless.

#### Step 1c — Already-connected server
MCP-Rubriq's own pipeline (Step 2) always makes its own fresh stdio/SSE/HTTP connection — there is no mechanism to reuse or introspect a connection Claude Code itself is already holding. So "already connected" is not a different way to skip Step 2; it's a different way to find the exact command/URL to feed into it.

If the user means a server already connected in this session (not one you need to guess a command for), find the config that established that connection — the same kind of file Step 1b already checks (`.mcp.json`, `claude_desktop_config.json`, etc.) — and extract its exact `command`/`args` or `url` from there. Then proceed to Step 2 normally with that verified value. Do not guess a command from the server's name alone just because it's already connected.

#### URL transport
If the target is a URL, determine whether it's SSE (`transport=sse`, e.g. a `/sse` path) or streamable HTTP (`transport=http`, the modern replacement for SSE, e.g. a `/mcp` path). If unsure which the server speaks, prefer `http` first — it's the current spec transport.

#### On failure: ask, don't guess again
Step 2's error output is specific (a real timeout, a real "connection closed" plus the server's actual stderr text — never an opaque generic message). Use that specific reason to either ask one targeted follow-up question or report the failure clearly to the user. **Do not silently retry with a different guessed command** (a different package name, a different flag, a different assumed path) — one failed attempt is a stopping point, not a cue to keep guessing.

### Step 2 — Run the Introspection & Annotation Pipeline
Execute the Python pipeline script located at `scripts/lint.py`, **relative to this SKILL.md's own directory** (i.e. the same `skills/mcp-rubriq/` folder this file lives in — resolve it to an absolute path based on wherever the plugin is actually installed, never assume a fixed machine-specific location). Invoke it via `uv run` — the script carries inline PEP 723 dependency metadata, so `uv` resolves `mcp`/`pydantic`/`anyio` into an ephemeral environment automatically on first use, with no manual `pip install` step required:
```bash
uv run "<this-skill-directory>/scripts/lint.py" --transport <stdio|sse|http> [ --command <command> | --url <url> ] [--env KEY=VALUE ...] [--header "NAME: VALUE" ...] [--cwd <absolute-folder-path>] [--timeout <seconds>] [--args TOKEN ...]
```
If `uv` isn't available on the user's machine, fall back to plain `python` (dropping `uv run` from the front of the command) — this requires `mcp`/`pydantic`/`anyio`/`httpx` to already be installed in whatever Python environment is active (`pip install -r <this-skill-directory>/introspection/requirements.txt`). Prefer `uv run` whenever `uv` is present; it's the zero-setup path.
- **If spawning `python`/`py` fails with an Application-Control-style error** (seen in practice on Windows machines under a locked-down IT policy: `error: Failed to spawn: 'python' ... An Application Control policy has blocked this file. (os error 4551)`) — this blocks the *target server's* subprocess, not `uv` itself, and is a client-machine policy issue, not something to keep guessing around. Recover in this order, once:
  1. Enumerate installed interpreters (`where python` / `where py` on Windows, `which -a python3` elsewhere).
  2. Test each candidate with `<candidate> -c "import httpx, mcp"` until one succeeds — that's an interpreter with the runtime deps already present, not just an alternate name for the same blocked binary.
  3. Re-run Step 2 directly with that interpreter's **absolute path**, for both the runner and the `--command`/target — i.e. drop `uv run` entirely for this path and invoke `lint.py` with that interpreter directly (`<absolute-path-to-python> "<this-skill-directory>/scripts/lint.py" ... --command "<same-absolute-path>" ...`). Mixing `uv run` with an Application-Control-restricted target has been observed to fail a second way (`uv`'s own ephemeral-env resolution for a *different* interpreter than the one that already worked once can miss `httpx`/`exceptiongroup` entirely) — going fully direct avoids both failure modes at once.
  If every discovered interpreter hits the same block, or none has the required packages, stop and report the exact error — this is the same "ask, don't guess again" rule as Step 1, not a cue to keep trying more interpreter names.
- Use `--env KEY=VALUE` (repeatable) to pass required environment variables (e.g. `GITHUB_TOKEN`, `BRAVE_API_KEY`) to a stdio server — check `known_servers.json`'s `env` list for the target to know which are required.
- **For an auth-protected `sse`/`http` server** (hosted/remote servers usually are), pass `--header` (repeatable), e.g. `--header "Authorization: Bearer $TOKEN"`. As with `--env` secrets, offer the user the shell-variable form first so the literal token never has to appear in the conversation. If the run fails with `401 Unauthorized`, report that the server requires credentials and ask what auth header to use — don't retry guessing.
- **For a stdio target resolved in Step 1b (a local/unpublished project), always pass `--cwd <the resolved folder's absolute path>`.** Without it, the server subprocess launches from wherever this shell's current directory happens to be, not the server's own directory — so a relative `--command`/`--args` (e.g. `python my_server.py`) silently fails to find the file unless the two happen to already match. This is what makes MCP-Rubriq work identically regardless of what directory it's actually invoked from.
- Use `--timeout` to override the default 30s if a server is slow to start (e.g. a cold `npx` install).
- **If any argument (most commonly a filesystem path) contains a space, pass it via `--args` as its own token instead of embedding it in `--command`.** An unquoted space inside `--command` is ambiguous and gets split into two arguments — e.g. `--command "npx -y @modelcontextprotocol/server-filesystem C:\Users\Jane Doe\project"` silently becomes three broken tokens. Use `--args "-y" "@modelcontextprotocol/server-filesystem" "C:\Users\Jane Doe\project"` instead — each `--args` token is passed through exactly as given, no splitting involved.
- **`--args` MUST be the last flag on the command line, always, with no exceptions** — it consumes every remaining token literally (including ones starting with `-`, like npx's `-y`), so put `--env`/`--header`/`--cwd`/`--timeout` *all before it, never after*. `--command "npx" --args "-y" "@pkg/foo"` is correct; `--command "npx" --args "-y" "@pkg/foo" --timeout 60` is not — `--timeout 60` would be swallowed into the args list instead of being parsed as a timeout. This has been observed happening live with `--cwd` specifically — double-check flag order before running, not just after a failure.

This script connects to the server, extracts raw metadata, and runs the Annotator engine to attach heuristic flags (facts) to each tool and property. It outputs the `AnnotatedServerModel` JSON to stdout.

### Step 3 — Load the Rubric
Use your `list_dir` and `view_file` capabilities to read all the markdown files located in `rulebook/rules/`, **relative to this SKILL.md's own directory** (a sibling of `scripts/` in this same skill folder).
These files contain the strict criteria for evaluating the server. **Do NOT skip reading these rules.** You need their precise pass/fail criteria to judge the server accurately.

### Step 4 — Act as the LLM Judge
You are the MCP-Rubriq judge. Evaluate the `AnnotatedServerModel` against the rules you just loaded.

**Your role:**
1. For each annotation flag on each tool/property, read the ACTUAL content (name, description, schema) and decide if the flag represents a REAL problem in context, or a FALSE POSITIVE. (E.g. A short description is not always bad. A destructive keyword in a tool name is not always undocumented). Use your judgment.
   1a. **Flags are attention hints, not a checklist.** The absence of a flag is not evidence of absence of a problem — every tool, resource, and prompt must still be evaluated against every applicable rule, including rules with no corresponding annotator flag at all (e.g. A002, A003, A005, X003). Do not limit evaluation to items the annotator happened to flag.
2. For semantic rules (vague descriptions, design patterns, security framing): evaluate the actual content against the rule criteria directly.
3. **Check `introspection_warnings` first.** If it's non-empty, part of the survey failed (a listing timed out or the server crashed mid-session) — every count affected by a failed listing is **unknown, not zero**. Never evaluate a rule against an empty list whose listing failed (e.g. don't fail A004 for "no prompts" when the warning says prompts couldn't be listed), and say prominently in the report that the evaluation was partial and why.
4. **The model also carries `resources`, `resource_templates`, and `prompts` — evaluate these too, not just `tools`.** Each now carries its own pre-computed `annotations` (description_missing, URI-template validity, ambiguous variable/argument names — see R001-R003), mirroring how tools carry theirs. Apply A004 against what resources/prompts actually exist (presence/absence only), R001-R003 against their content quality once present, and X005's injection scan to *their* descriptions and URI templates as well as to tool descriptions — server metadata of every kind is read by the calling model as trusted context.
5. **Each tool also carries `tool_annotations`** — the MCP spec's own `readOnlyHint`/`destructiveHint`/`idempotentHint`/`openWorldHint`, forwarded verbatim (`null` if the server declared none). These are **untrusted hints a server can lie about** — never treat them as proof a tool is safe. Use them per T007 and X001: a declared hint that contradicts the tool's own name/description (e.g. `readOnlyHint: true` on an evident delete tool) is an aggravating finding, not a mitigating one.
6. Determine if the server passes or fails each rule. **Only report findings you can support with specific evidence from the server data.**

### Step 5 — Present the Report
Present a final, structured Markdown report to the user. The report should include:

1. **Server Summary:** A brief 2-3 sentence assessment of the server's overall quality and capabilities.
2. **Findings:** Grouped by severity (Error -> Warning -> Info). For every finding include:
   - **Rule ID & Name**
   - **Target** (e.g., `tool:delete_file`, `server`)
   - **Evidence:** The exact text/value from the server that is the problem.
   - **Suggestion:** A concrete, actionable fix.
3. **Passed Rules:** A list of rules that were evaluated and found to have no issues.
4. **Skipped Rules:** Any rules that were not applicable (e.g., capability rules if absent by design), along with a brief reason.

*Note: All X-series (Security) findings should be framed with advisory language: "This pattern may indicate a security concern. Manual review recommended."*
