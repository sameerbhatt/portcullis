"""portcullis: a per-action autonomy policy layer for AI agents.

Decide, per tool call, whether an agent may act on its own -- based on the
action's reversibility and blast radius, not the model's capability.
"""

from .core import (
    ActionDenied,
    ActionProfile,
    ApprovalHandler,
    AuditLog,
    AutoApprove,
    BlastRadius,
    CallbackApproval,
    CLIApproval,
    Decision,
    GovernanceEngine,
    Outcome,
    Policy,
    Reversibility,
    decide,
)

__version__ = "0.1.0"

__all__ = [
    "ActionDenied",
    "ActionProfile",
    "ApprovalHandler",
    "AuditLog",
    "AutoApprove",
    "BlastRadius",
    "CallbackApproval",
    "CLIApproval",
    "Decision",
    "GovernanceEngine",
    "Outcome",
    "Policy",
    "Reversibility",
    "decide",
    "__version__",
]
