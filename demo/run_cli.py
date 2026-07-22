"""CLI demo: watch the governance layer make live decisions.

Runs an agent through a realistic task that touches all four tools. Each
tool call is routed through the GovernanceEngine, which prints the decision
and its 2x2 cell before executing -- or pausing for you to approve.

Two modes:
  * with OPENAI_API_KEY set and langgraph installed -> a real LangGraph agent
    plans the tool calls.
  * otherwise -> a scripted plan runs, so the demo always works and always
    produces the same shareable output.

Run:
    python demo/run_cli.py            # auto-detects mode
    python demo/run_cli.py --scripted # force the scripted plan
    python demo/run_cli.py --auto-approve  # non-interactive (for GIF capture)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from portcullis import (  # noqa: E402
    ActionDenied,
    AuditLog,
    AutoApprove,
    CLIApproval,
    GovernanceEngine,
)
from tools import TOOLS, build_policy  # noqa: E402


C = {
    "allow": "\033[32m",            # green
    "allow_with_audit": "\033[33m",  # yellow
    "require_approval": "\033[35m",  # magenta
    "dim": "\033[90m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}

# A realistic support-automation task, ordered so the stakes escalate: two
# free reads, two writes that run but leave a record, then two irreversible
# actions that must pause. Every cell of the matrix is touched.
SCRIPTED_PLAN = [
    ("search_web", {"query": "Acme Corp refund policy"}),
    ("read_customer", {"customer_id": "C-4821"}),
    ("write_audit_note", {"customer_id": "C-4821", "note": "refund approved under policy 4.2"}),
    ("retag_open_tickets", {"tag": "refund-window-2026Q3"}),
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


def print_decision(step: int, name: str, args: dict, decision) -> None:
    color = C.get(decision.outcome, "")
    cell = CELL.get((decision.reversibility, decision.blast_radius), "")
    arg_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
    print(f"\n{C['bold']}[{step}] {name}({arg_str}){C['reset']}")
    print(f"    cell    : {cell}")
    print(f"    outcome : {color}{decision.outcome.replace('_', ' ').upper()}{C['reset']}")
    print(f"    {C['dim']}reason  : {decision.reason}{C['reset']}")


def run(scripted: bool, auto_approve: bool) -> None:
    policy = build_policy()
    audit_path = Path(__file__).parent / "audit_log.jsonl"
    if audit_path.exists():
        audit_path.unlink()
    audit = AuditLog(audit_path)
    approval = AutoApprove(approve=True) if auto_approve else CLIApproval()
    engine = GovernanceEngine(policy, approval=approval, audit=audit)

    banner("portcullis  ::  live decision demo")
    print("Task: process a refund for customer C-4821, then clean up the record.")
    print(f"{C['dim']}Each tool call is judged on reversibility x blast radius, "
          f"not on how capable the agent is.{C['reset']}")

    plan = SCRIPTED_PLAN  # real-agent planning is wired in run_agent(); MVP uses scripted
    for i, (name, args) in enumerate(plan, 1):
        decision = engine.evaluate(name, arguments=args)
        print_decision(i, name, args, decision)
        try:
            result = engine.guard(name, TOOLS[name], **args)
            print(f"    {C['dim']}result  : {result}{C['reset']}")
        except ActionDenied:
            print(f"    {C['require_approval']}BLOCKED : human declined; "
                  f"agent cannot proceed with this action.{C['reset']}")

    banner("run summary")
    for outcome, count in audit.summary().items():
        print(f"    {outcome:<18}: {count}")
    print(f"\n{C['dim']}Full audit trail written to {audit_path}{C['reset']}\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripted", action="store_true", help="force the scripted plan")
    ap.add_argument("--auto-approve", action="store_true", help="approve all pauses (non-interactive)")
    args = ap.parse_args()

    has_key = bool(os.getenv("OPENAI_API_KEY"))
    scripted = args.scripted or not has_key
    if not scripted:
        print(f"{C['dim']}(OPENAI_API_KEY detected -- a real agent adapter would plan here; "
              f"MVP runs the scripted plan for a deterministic demo.){C['reset']}")
    run(scripted=scripted, auto_approve=args.auto_approve)


if __name__ == "__main__":
    main()
