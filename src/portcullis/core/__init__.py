"""Framework-agnostic core of the portcullis library.

Nothing in this package imports LangGraph, LangChain, or any LLM SDK.
The governance model stands on its own and is fully testable without an
API key. Framework adapters live in `portcullis.adapters`.
"""

from .approval import (
    ApprovalHandler,
    AutoApprove,
    CallbackApproval,
    CLIApproval,
)
from .audit import AuditLog
from .engine import ActionDenied, GovernanceEngine
from .model import (
    ActionProfile,
    BlastRadius,
    Decision,
    Outcome,
    Reversibility,
    decide,
)
from .policy import Policy

__all__ = [
    "ApprovalHandler",
    "AutoApprove",
    "CallbackApproval",
    "CLIApproval",
    "AuditLog",
    "ActionDenied",
    "GovernanceEngine",
    "ActionProfile",
    "BlastRadius",
    "Decision",
    "Outcome",
    "Reversibility",
    "decide",
    "Policy",
]
