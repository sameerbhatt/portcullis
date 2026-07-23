# portcullis

[![PyPI](https://img.shields.io/pypi/v/portcullis.svg)](https://pypi.org/project/portcullis/)
[![Python](https://img.shields.io/pypi/pyversions/portcullis.svg)](https://pypi.org/project/portcullis/)
[![CI](https://github.com/sameerbhatt/portcullis/actions/workflows/ci.yml/badge.svg)](https://github.com/sameerbhatt/portcullis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/sameerbhatt/portcullis/blob/main/LICENSE)

**A per-action autonomy policy layer for AI agents.**

```bash
pip install portcullis
```

Decide, for every tool call, whether an agent may act on its own — based on
the *action's* reversibility and blast radius, not the *model's* capability.

Everyone is building more capable agents. Almost no one is building the layer
that decides what an agent is allowed to do without asking. This is that layer.

---

## The idea in one table

Two properties of an action decide everything:

- **Reversibility** — can the effect be undone? (reading a row is reversible; sending an email is not)
- **Blast radius** — how far do the consequences reach? (one record vs. a whole table)

Map every tool call onto the grid, and the cell decides the outcome:

|                | Low blast radius   | High blast radius     |
| -------------- | ------------------ | --------------------- |
| **Reversible** | auto-execute       | execute + audit       |
| **Irreversible** | execute + audit  | **require approval**  |

The point most designs miss: **capability is irrelevant to this decision.**
A smarter model does not move `delete_production_table` out of the "require
approval" cell. That is what makes this *governance* and not a guardrail.

## Quickstart

```python
from portcullis import (
    Policy, GovernanceEngine, Reversibility, BlastRadius, CLIApproval,
)

policy = (
    Policy()
    .register("read_customer", Reversibility.REVERSIBLE,   BlastRadius.LOW)
    .register("send_email",    Reversibility.IRREVERSIBLE, BlastRadius.HIGH)
)

engine = GovernanceEngine(policy, approval=CLIApproval())

# reversible + low  -> runs immediately
engine.guard("read_customer", read_customer, "C-4821")

# irreversible + high -> pauses and asks a human; raises ActionDenied if declined
engine.guard("send_email", send_email, to="billing@acme.com", subject="Refund")
```

### With LangGraph

```python
from portcullis.adapters.langgraph import govern_all

governed_tools = govern_all(engine, tools)   # drop into your graph unchanged
```

The adapter returns tools of the same shape (a `BaseTool` stays a `BaseTool`),
so an existing graph needs no other changes.

## Demo

Run these from a clone of the repository — see [From source](#from-source).

```bash
python demo/run_cli.py            # live decisions in the terminal
python demo/run_cli.py --auto-approve   # non-interactive (for capture)
open demo/web/index.html          # the visual decision console
```

The demo runs one refund-processing task whose six actions touch all four
cells, with the stakes escalating as it goes: two reversible reads
auto-execute, two writes in the mixed cells execute but are recorded, and two
irreversible high-blast-radius actions pause for a human.

The middle pair is the one worth watching. `write_audit_note` cannot be undone
but touches a single record; `retag_open_tickets` is trivially undone but
writes across the whole queue. Neither is dangerous enough to stop the agent,
and neither should pass without leaving a trail — which is exactly what the
two mixed cells are for.

### The same governance, inside a LangGraph graph

From a clone (see [From source](#from-source) — the demo scripts ship with
the repository, not with the package):

```bash
pip install -e ".[langgraph]"
python demo/run_langgraph.py                # interactive approvals
python demo/run_langgraph.py --auto-approve  # non-interactive (for capture)
python demo/run_langgraph.py --deny-all      # show fail-closed denials
```

`run_langgraph.py` runs the *same* task through an actual LangGraph
`StateGraph` (`planner → ToolNode → loop`). The tools are ordinary LangChain
`@tool` tools; governance is added by wrapping them with `govern_all`, not by
editing the graph. A denied action raises `ActionDenied`, which `ToolNode`
surfaces to the agent as a real tool error. The planner is scripted so the
demo is deterministic and needs no API key — swap in `create_react_agent`
with an LLM and the governed tools drop in unchanged.

## Design choices

- **Core is dependency-free.** Nothing in `portcullis.core` imports
  LangChain or any LLM SDK. The governance model is fully unit-tested without
  an API key — you can read and trust it on its own.
- **Fail-closed by default.** An undeclared tool is treated as the most
  dangerous cell (irreversible + high), so unknown actions pause rather than
  slip through.
- **Denials raise, they don't return sentinels.** A blocked action raises
  `ActionDenied`, so your agent framework sees a real, catchable failure.
- **Every decision is audited.** Append-only JSONL: your answer to "why did
  the agent do that?"

## Future roadmap: Not in v0.1

- LLM-assisted classification of reversibility/blast radius (v0.1: you declare it)
- Web / Slack approval handlers and multi-approver RBAC (the interface is ready)
- Persistence beyond a JSONL audit file

These are intentional cuts to keep the core small and legible. The interfaces
(`ApprovalHandler`, adapters) are shaped so each is an addition, not a rewrite.

## Install

```bash
pip install portcullis                # core only, zero dependencies
pip install "portcullis[langgraph]"   # + LangGraph adapter
```

Requires Python 3.10+. The core has no dependencies at all, so the first
line pulls in nothing but the package itself.

### From source

The demo scripts live in the repository, not in the published package, so
running them means cloning first:

```bash
git clone https://github.com/sameerbhatt/portcullis.git
cd portcullis
pip install -e ".[demo]"    # everything needed to run the demo
pip install -e ".[dev]"     # core + pytest, to run the suite
pytest -q
```

## License

MIT.
