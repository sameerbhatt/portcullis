# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

`portcullis` — a per-action autonomy policy layer for AI agents. It
decides, for every tool call, whether an agent may act on its own, based on
the **action's** reversibility and blast radius rather than the **model's**
capability.

The one claim the whole library defends:

    decide(reversibility, blast_radius) -> outcome

A more capable model does **not** move an action out of the "require approval"
cell. That is what makes this governance, not a guardrail. Keep this framing
intact in any change — code, docs, or demo.

## The decision model (do not silently change)

Two axes, four cells:

|                | Low blast radius | High blast radius   |
| -------------- | ---------------- | ------------------- |
| Reversible     | ALLOW            | ALLOW_WITH_AUDIT    |
| Irreversible   | ALLOW_WITH_AUDIT | REQUIRE_APPROVAL    |

Only the irreversible + high cell stops the agent. This table lives in
`core/model.py::decide`. If a change alters this matrix, call it out
explicitly and update the README table, the tests, and the demo in the same
change — these four must always agree.

## Architecture — three layers, strict dependency direction

```
src/portcullis/
  core/          # NO langchain, NO llm sdk imports. Ever.
    model.py     #   Reversibility, BlastRadius, Outcome, ActionProfile, decide()
    policy.py    #   Policy registry; fail-closed default for undeclared tools
    approval.py  #   ApprovalHandler protocol + CLI/Auto/Callback impls
    audit.py     #   append-only JSONL AuditLog + observer hook
    engine.py    #   GovernanceEngine.guard(); raises ActionDenied on denial
  adapters/
    langgraph.py # the ONLY module that imports langchain (deferred import)
demo/
  tools.py         # 4 toy tools spanning all 4 cells + declared Policy
  run_cli.py       # deterministic scripted plan; --auto-approve for capture
  run_langgraph.py # same task inside a real LangGraph StateGraph via the adapter
  web/index.html   # self-contained "decision console" (the hero visual)
tests/
  test_core.py   # 9 tests; run with no API key, no network
```

**Hard invariant:** `core/` must never import langchain, langgraph, or any
LLM SDK. The test of correctness is that `tests/` passes with none of them
installed. Any framework code goes in `adapters/`. If you add a second
framework (CrewAI, etc.), it is a new adapter, never a change to core.

## Design invariants (preserve these)

- **Fail-closed by default.** An undeclared tool is treated as the most
  dangerous cell (irreversible + high) so unknown actions pause. Do not flip
  the default to fail-open.
- **Denials raise, they don't return sentinels.** A blocked action raises
  `ActionDenied` so the agent framework sees a real, catchable failure.
- **Every decision is audited.** All four outcomes get recorded, not just the
  paused ones — the audit trail must be complete.
- **The core stays dependency-free.** `dependencies = []` in pyproject.
  Anything heavier goes behind an optional extra.
- **Legibility over cleverness.** The governance rule must stay explainable in
  one table. Reject changes that make the decision harder to reason about.

## Commands

```bash
pip install -e ".[dev]"            # core + pytest
pip install -e ".[langgraph]"      # + LangGraph adapter deps
pip install -e ".[demo]"           # + everything for the demo
pytest -q                          # run the suite (no API key needed)
python demo/run_cli.py             # live decisions in the terminal
python demo/run_cli.py --auto-approve   # non-interactive (GIF/screenshot)
python demo/run_langgraph.py       # same task inside a real LangGraph graph
open demo/web/index.html           # the visual decision console
```

## Conventions

- Python >= 3.10, standard library only in `core/`.
- Type hints throughout; `from __future__ import annotations` at the top of
  each module.
- Docstrings explain the *why* (the governance reasoning), not just the what —
  this repo is meant to be read as an argument, not just run.
- Keep public API changes reflected in both `core/__init__.py` and the
  top-level `__init__.py` (they re-export the same names).
- When you touch behavior, add or update a test in `tests/test_core.py`. The
  suite must stay green and must not require credentials.

## Roadmap — deliberately deferred (v2), not gaps

These are intentional cuts. If asked to add one, it should slot in as an
addition, not a rewrite — the interfaces are already shaped for them:

- LLM-assisted auto-classification of reversibility/blast radius (v0.1: the
  user declares profiles explicitly, on purpose).
- Web / Slack approval handlers, multi-approver RBAC — all just new
  `ApprovalHandler` implementations.
- Persistence beyond the JSONL audit file.
- An LLM-driven planning path in the demo. `demo/run_langgraph.py` already
  runs the governed tools inside a real LangGraph `StateGraph`, but with a
  scripted planner node for determinism; swapping it for `create_react_agent`
  + an LLM is the remaining v2 step (the governed tools drop in unchanged).
