"""The governance engine.

This is the piece that sits between an agent and its tools. For every
proposed tool call it:

    1. looks up the tool's action profile in the policy
    2. runs the decision function -> an Outcome
    3. enforces the Outcome:
         ALLOW              -> execute
         ALLOW_WITH_AUDIT   -> execute, and record the decision
         REQUIRE_APPROVAL   -> ask the approval handler; execute iff approved
    4. records every decision in the audit log

Denied actions raise ActionDenied rather than returning a sentinel, so the
agent framework sees a real, catchable failure instead of a silent no-op.
"""

from __future__ import annotations

from typing import Any, Callable

from .approval import ApprovalHandler, AutoApprove
from .audit import AuditLog
from .model import Decision, Outcome, decide
from .policy import Policy


class ActionDenied(Exception):
    """Raised when a REQUIRE_APPROVAL action is not approved by a human."""

    def __init__(self, decision: Decision) -> None:
        self.decision = decision
        super().__init__(
            f"action '{decision.action}' denied: {decision.reason}"
        )


class GovernanceEngine:
    def __init__(
        self,
        policy: Policy,
        approval: ApprovalHandler | None = None,
        audit: AuditLog | None = None,
    ) -> None:
        self.policy = policy
        self.approval = approval or AutoApprove(approve=False)
        self.audit = audit or AuditLog()

    def evaluate(self, tool_name: str, arguments: dict | None = None) -> Decision:
        """Run the decision for a tool call without executing it.

        Exposed on its own so a UI can preview what *would* happen, and so
        the decision can be inspected in tests.
        """
        profile = self.policy.profile_for(tool_name)
        outcome = decide(profile)
        return Decision.from_profile(profile, outcome, arguments)

    def guard(
        self,
        tool_name: str,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Govern a single call to `fn`, then execute or block it.

        `fn` is the real tool implementation. Positional/keyword args are
        passed straight through on execution.
        """
        decision = self.evaluate(tool_name, arguments=_describe_args(args, kwargs))
        outcome = Outcome(decision.outcome)

        if outcome is Outcome.REQUIRE_APPROVAL:
            approved = self.approval.request(decision)
            decision.approved = approved
            self.audit.record(decision)
            if not approved:
                raise ActionDenied(decision)
            return fn(*args, **kwargs)

        if outcome is Outcome.ALLOW_WITH_AUDIT:
            self.audit.record(decision)
            return fn(*args, **kwargs)

        # ALLOW: execute; recording is optional but we log for a complete trace
        self.audit.record(decision)
        return fn(*args, **kwargs)


def _describe_args(args: tuple, kwargs: dict) -> dict:
    """Best-effort, JSON-friendly snapshot of call arguments for the audit."""
    out: dict[str, Any] = {}
    for i, a in enumerate(args):
        out[f"arg{i}"] = _safe(a)
    for k, v in kwargs.items():
        out[k] = _safe(v)
    return out


def _safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    text = repr(value)
    return text if len(text) <= 120 else text[:117] + "..."
