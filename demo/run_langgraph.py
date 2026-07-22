"""LangGraph demo: the governance layer running inside a real graph.

The CLI demo (`run_cli.py`) routes a *scripted* list of calls through the
engine directly. This demo does the same governance, but the calls flow
through an actual LangGraph `StateGraph`: a planner node emits tool calls,
a `ToolNode` executes them, and every execution passes through the
governed wrappers produced by `adapters.langgraph.govern_all`.

Why a scripted planner instead of an LLM? The same reason the CLI demo is
deterministic: the point on display is *governance*, not planning. Swap the
`planner` node for `create_react_agent` (with an OPENAI_API_KEY) and the
graph is unchanged -- the governed tools drop in exactly the same way. That
substitutability is the whole argument of the adapter.

What to watch: the tools are ordinary LangChain tools. Governance is added
by wrapping them, not by editing the graph. When an irreversible + high
blast-radius call is denied, the engine raises `ActionDenied`; LangGraph's
`ToolNode` surfaces it to the agent as a real tool error -- a catchable
failure, not a silent no-op.

Run:
    pip install -e ".[langgraph]"
    python demo/run_langgraph.py               # interactive approvals
    python demo/run_langgraph.py --auto-approve # non-interactive (GIF capture)
    python demo/run_langgraph.py --deny-all     # show fail-closed denials
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from portcullis import (  # noqa: E402
    AutoApprove,
    CLIApproval,
    GovernanceEngine,
    AuditLog,
)
from portcullis.adapters.langgraph import govern_all  # noqa: E402
import tools as demo_tools  # noqa: E402


C = {
    "allow": "\033[32m",
    "allow_with_audit": "\033[33m",
    "require_approval": "\033[35m",
    "denied": "\033[31m",
    "dim": "\033[90m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}

# Same realistic support task as the CLI demo, so the two are comparable.
PLAN = [
    ("search_web", {"query": "Acme Corp refund policy"}),
    ("read_customer", {"customer_id": "C-4821"}),
    ("send_email", {"to": "billing@acme.com", "subject": "Refund processed"}),
    ("delete_customer", {"customer_id": "C-4821"}),
]

CELL = {
    ("reversible", "low"): "reversible + low blast radius",
    ("reversible", "high"): "reversible + high blast radius",
    ("irreversible", "low"): "irreversible + low blast radius",
    ("irreversible", "high"): "irreversible + high blast radius",
}


def banner(text: str) -> None:
    print(f"\n{C['bold']}{text}{C['reset']}")
    print(C["dim"] + "-" * 66 + C["reset"])


def _require_langgraph():
    """Import LangGraph/LangChain, or explain how to get them and exit."""
    try:
        from langchain_core.tools import tool
        from langchain_core.messages import AIMessage, ToolMessage
        from langgraph.graph import StateGraph, END
        from langgraph.graph.message import add_messages
        from langgraph.prebuilt import ToolNode
    except ImportError as exc:  # pragma: no cover - environment-dependent
        print(
            f"{C['denied']}This demo needs the LangGraph adapter dependencies.{C['reset']}\n"
            f"Install them with:\n\n    pip install -e \".[langgraph]\"\n\n"
            f"(missing import: {exc.name})\n\n"
            f"The core library and the CLI demo (`python demo/run_cli.py`) run\n"
            f"without any of this -- governance is framework-agnostic on purpose."
        )
        raise SystemExit(1)
    return tool, AIMessage, ToolMessage, StateGraph, END, add_messages, ToolNode


def build_tools(tool_decorator):
    """Four ordinary LangChain tools -- no governance knowledge in them.

    They delegate to the plain functions in demo/tools.py so behaviour stays
    single-sourced with the CLI demo. Governance is layered on afterward by
    wrapping, never by changing these definitions.
    """

    @tool_decorator
    def search_web(query: str) -> str:
        """Search the public web for information."""
        return demo_tools.search_web(query)

    @tool_decorator
    def read_customer(customer_id: str) -> str:
        """Read a single internal customer record."""
        return demo_tools.read_customer(customer_id)

    @tool_decorator
    def send_email(to: str, subject: str) -> str:
        """Send an email to an external recipient."""
        return demo_tools.send_email(to, subject)

    @tool_decorator
    def delete_customer(customer_id: str) -> str:
        """Permanently delete a production customer record."""
        return demo_tools.delete_customer(customer_id)

    return [search_web, read_customer, send_email, delete_customer]


def make_decision_printer():
    """An audit observer that prints each decision as the graph runs."""
    counter = {"n": 0}

    def on_decision(decision) -> None:
        counter["n"] += 1
        color = C.get(decision.outcome, "")
        cell = CELL.get((decision.reversibility, decision.blast_radius), "")
        args = ", ".join(f"{k}={v!r}" for k, v in decision.arguments.items())
        print(f"\n{C['bold']}[{counter['n']}] {decision.action}({args}){C['reset']}")
        print(f"    cell    : {cell}")
        print(f"    outcome : {color}{decision.outcome.replace('_', ' ').upper()}{C['reset']}")
        print(f"    {C['dim']}reason  : {decision.reason}{C['reset']}")
        if decision.approved is False:
            print(f"    {C['denied']}BLOCKED : denied -> ToolNode will report a tool error "
                  f"to the agent.{C['reset']}")

    return on_decision


def build_graph(governed_tools, deps):
    """A minimal but genuine LangGraph: planner -> governed tools -> loop."""
    tool, AIMessage, ToolMessage, StateGraph, END, add_messages, ToolNode = deps
    # MessagesState is LangGraph's built-in {"messages": add_messages} schema.
    # Using it avoids re-declaring an Annotated TypedDict (whose forward-ref
    # annotations don't resolve cleanly under `from __future__ import annotations`).
    from langgraph.graph import MessagesState

    # Note: no parameter type hints on these nodes. LangGraph runs
    # get_type_hints() on node/branch callables, and a forward-ref to the
    # function-local MessagesState won't resolve under `from __future__
    # import annotations`. The state is a plain dict at runtime regardless.
    def planner(state):
        # Deterministic "planning": advance through PLAN by how many tool
        # calls have already completed. An LLM planner would slot in here.
        done = sum(1 for m in state["messages"] if isinstance(m, ToolMessage))
        if done >= len(PLAN):
            return {"messages": [AIMessage(content="All planned steps complete.")]}
        name, args = PLAN[done]
        call = {"name": name, "args": args, "id": f"call_{done}"}
        return {"messages": [AIMessage(content="", tool_calls=[call])]}

    def route(state):
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    graph = StateGraph(MessagesState)
    graph.add_node("planner", planner)
    graph.add_node("tools", ToolNode(governed_tools))
    graph.set_entry_point("planner")
    graph.add_conditional_edges("planner", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "planner")
    return graph.compile()


def run(auto_approve: bool, deny_all: bool) -> None:
    deps = _require_langgraph()
    tool_decorator = deps[0]

    policy = demo_tools.build_policy()
    audit_path = Path(__file__).parent / "audit_log.jsonl"
    if audit_path.exists():
        audit_path.unlink()
    audit = AuditLog(audit_path)
    audit.subscribe(make_decision_printer())

    if deny_all:
        approval = AutoApprove(approve=False)   # fail-closed: nothing risky runs
    elif auto_approve:
        approval = AutoApprove(approve=True)
    else:
        approval = CLIApproval()

    engine = GovernanceEngine(policy, approval=approval, audit=audit)

    raw_tools = build_tools(tool_decorator)
    governed_tools = govern_all(engine, raw_tools)   # <-- the whole integration
    app = build_graph(governed_tools, deps)

    banner("portcullis  ::  LangGraph decision demo")
    print("Task: process a refund for customer C-4821, then clean up the record.")
    print(f"{C['dim']}Ordinary LangChain tools, run inside a LangGraph StateGraph. "
          f"Governance is added by wrapping the tools, not by editing the graph.{C['reset']}")

    from langchain_core.messages import HumanMessage
    app.invoke(
        {"messages": [HumanMessage(content="Process the C-4821 refund and clean up.")]},
        config={"recursion_limit": 50},
    )

    banner("run summary")
    for outcome, count in audit.summary().items():
        print(f"    {outcome:<18}: {count}")
    print(f"\n{C['dim']}Full audit trail written to {audit_path}{C['reset']}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Governed tools inside a LangGraph graph.")
    ap.add_argument("--auto-approve", action="store_true",
                    help="approve all pauses (non-interactive)")
    ap.add_argument("--deny-all", action="store_true",
                    help="deny every approval -> show fail-closed denials")
    args = ap.parse_args()
    run(auto_approve=args.auto_approve, deny_all=args.deny_all)


if __name__ == "__main__":
    main()
