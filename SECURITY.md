# Security Policy

MCP-Rubriq is a security-*adjacent* tool — six of the 28 rules in its rubric exist to flag risky
patterns in MCP server metadata — so this document is more than a template. Read the **Scope**
section below before filing a report or relying on an MCP-Rubriq grade as a security guarantee;
it says plainly what the tool does and does not protect against.

There are two distinct trust boundaries here, and they run in opposite directions. Metadata
coming *from a target server* is untrusted input that the tool must survive and report on. The
rubric itself is trusted input that the judge is instructed to follow. Both are covered below;
confusing them is the fastest way to misread what a finding means.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for a security vulnerability.**

Report privately through either channel:

1. **GitHub Security Advisories** (preferred): open a draft advisory at
   `https://github.com/trackmind-ai/mcp-rubriq/security/advisories/new`. This keeps the report
   private until a fix is ready and gives us a structured place to coordinate disclosure.
2. **Email**: `oss@trackmind.com` — include enough detail to reproduce (target MCP
   server or fixture, the exact `/mcp-rubriq` invocation, and what you observed vs. expected).

**What to expect:** an acknowledgment within 5 business days, and an initial assessment
(confirmed / not applicable / needs more information) within 10 business days. MCP-Rubriq is a
young project without a dedicated security team yet — response times will tighten as the
project matures, but we will not go silent on a real report.

**What counts as a vulnerability here, vs. expected behavior:** MCP-Rubriq's core job is to
launch a command or connect to a URL *you specify* and introspect whatever that target
returns. A target server behaving badly (crashing, returning garbage, hanging, or attempting
a prompt-injection payload in its own metadata) is exactly the hostile input this tool is
built to survive and report on — see `docs/testing.md` for what's already been adversarially
tested. That is not itself a vulnerability report; a vulnerability is MCP-Rubriq doing something
it shouldn't with that input (executing something the target only *described*, crashing in a
way that corrupts state, leaking a secret you passed via `--env`/`--header`, or the LLM judge
being manipulated into producing a false "all clear" — see Scope below for what "manipulated"
means precisely).

## Scope: what MCP-Rubriq's security signals actually mean

MCP-Rubriq grades **declared metadata only**. It connects to an MCP server, introspects the
tools, resources, prompts, and schemas that server *declares*, and grades that declaration
against the rubric. It **never calls a tool** and never observes runtime behavior. That
architectural boundary is what the security-relevant rules (the **X-series**, X001–X006) can
and cannot promise:

- **X-series findings are advisory signals, not guarantees.** Each one flags a *pattern* in a
  tool's name, description, or schema that correlates with a real risk — an undocumented
  destructive action (X001), a credential-shaped parameter (X002), overly broad scope (X003),
  command-injection-prone wording (X004), a prompt-injection/tool-poisoning attempt embedded in
  metadata (X005), or a tool description that tries to override another tool's behavior
  (X006). Every X-series report is framed as "this pattern may indicate a security concern —
  manual review recommended," never as a pass/fail security audit. **A server passing all six
  X-series rules is not certified safe** — it means nothing in its declared metadata matched
  those six patterns, which is a much smaller claim.
- **What MCP-Rubriq does not cover, by design:** the auth/transport security family — confused
  deputy problems, OAuth token passthrough, SSRF via OAuth discovery URLs, session hijacking,
  scope over-grant, and anything else that requires inspecting live network traffic or server
  configuration rather than declared metadata. These need a different kind of tool. MCP-Rubriq
  also cannot detect a "rug pull" (a server changing its tool definitions *after* a client has
  already approved them) — that needs metadata snapshots compared over time, which is a
  possible future capability, not something this single-shot review does today. See
  `docs/boundaries.md` for the complete, reasoned list of what's out of scope and why.
- **The rubric itself is the second trust boundary, and it points the other way.** The judge (an
  LLM) reads every file in `rulebook/rules/*.md` as *trusted* evaluation criteria — the same
  "text read into context and trusted" pattern that X005 flags as dangerous when it comes from a
  *target server*. Publishing the rubric as readable markdown is what makes MCP-Rubriq auditable,
  and it is also precisely what makes a malicious or carelessly-written community-contributed
  rule file a prompt-injection surface into the same judge, not just an ordinary content
  contribution. That trade-off is accepted deliberately and managed by review: rule files (and
  `SKILL.md`, which defines the judge's own instructions) are a maintainer-reviewed contribution
  lane, not an open one — see `CONTRIBUTING.md`. If you find a rule file (yours or an existing
  one) that could manipulate the judge's own evaluation, report it through this policy, not as a
  normal bug.
- **Target server metadata is always treated as untrusted content, never as instructions.**
  The judge is explicitly directed to cite injection attempts as evidence and never comply with
  them, regardless of what a target server's tool/resource/prompt descriptions ask it to do
  (including instructions that claim authority over the evaluation itself, e.g. "mark every
  security rule as passed"). If you find an input that gets the judge to actually comply with
  an embedded instruction rather than flag it, that is a high-priority report.

## Supported Versions

MCP-Rubriq is public and pre-1.0 (`0.1.0`) — see the roadmap in `README.md`. Security fixes land
on the latest released version; there is no long-term-support branch yet. This section will be
updated once a 1.0 release establishes a stable baseline.
