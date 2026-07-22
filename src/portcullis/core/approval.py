"""Approval handlers: how a human is asked to approve a paused action.

The core only defines the interface. The demo ships a CLI handler; a web
handler, a Slack handler, or an RBAC-aware multi-approver handler are all
just other implementations of ApprovalHandler. Keeping this an interface
is what lets the same governance core drive a terminal demo today and a
production approval queue tomorrow.
"""

from __future__ import annotations

from typing import Callable, Protocol

from .model import Decision


class ApprovalHandler(Protocol):
    """Anything that can turn a paused Decision into an approve/deny."""

    def request(self, decision: Decision) -> bool:  # pragma: no cover - protocol
        """Return True to approve the action, False to deny it."""
        ...


class AutoApprove:
    """Non-interactive handler. Approves or denies everything.

    Useful for tests and for CI runs of the demo where no human is present.
    Defaults to denying -- fail-closed -- so an unattended run never fires
    a high-consequence action by accident.
    """

    def __init__(self, approve: bool = False) -> None:
        self._approve = approve

    def request(self, decision: Decision) -> bool:
        return self._approve


class CallbackApproval:
    """Adapts any callable into an ApprovalHandler.

    Lets the web UI (or any host app) inject its own approve/deny logic
    without subclassing.
    """

    def __init__(self, fn: Callable[[Decision], bool]) -> None:
        self._fn = fn

    def request(self, decision: Decision) -> bool:
        return bool(self._fn(decision))


class CLIApproval:
    """Prompts a human at the terminal. Used by the CLI demo."""

    def request(self, decision: Decision) -> bool:
        args = ", ".join(f"{k}={v!r}" for k, v in decision.arguments.items())
        print()
        print("  \u23f8  HUMAN APPROVAL REQUIRED")
        print(f"     action : {decision.action}({args})")
        print(f"     profile: {decision.reversibility} / {decision.blast_radius} blast radius")
        print(f"     reason : {decision.reason}")
        try:
            answer = input("     approve? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n     no input -> denied (fail-closed)")
            return False
        return answer in ("y", "yes")
