"""Core domain model for portcullis: governed autonomy for AI agents.

The central claim of this library: an agent's autonomy on a given action
should be decided by two properties of the *action*, not by the capability
of the *agent*.

    reversibility x blast_radius  ->  autonomy outcome

A more powerful model does not move an action out of the "requires human
approval" cell. That is what makes this a governance layer rather than a
guardrail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Reversibility(Enum):
    """Can the effect of this action be undone?"""

    REVERSIBLE = "reversible"        # reading a file, querying a row
    IRREVERSIBLE = "irreversible"    # sending an email, deleting a record


class BlastRadius(Enum):
    """How far do the consequences of this action reach?"""

    LOW = "low"      # affects a single item, scoped, contained
    HIGH = "high"    # affects many items, external parties, production


class Outcome(Enum):
    """What the governance layer decides to do with a proposed action."""

    ALLOW = "allow"                          # auto-execute, no record needed
    ALLOW_WITH_AUDIT = "allow_with_audit"    # execute, but record the decision
    REQUIRE_APPROVAL = "require_approval"     # pause; a human must approve


@dataclass(frozen=True)
class ActionProfile:
    """The governance-relevant profile of a single tool/action.

    This is deliberately small. Everything the decision function needs
    lives here, and nothing about the model, the prompt, or the agent's
    "intelligence" is present -- by design.
    """

    name: str
    reversibility: Reversibility
    blast_radius: BlastRadius
    description: str = ""


def decide(profile: ActionProfile) -> Outcome:
    """The signature decision function: (reversibility, blast_radius) -> Outcome.

    The 2x2:

                      LOW blast radius        HIGH blast radius
        REVERSIBLE    ALLOW                   ALLOW_WITH_AUDIT
        IRREVERSIBLE  ALLOW_WITH_AUDIT        REQUIRE_APPROVAL

    The only cell that stops the agent is irreversible + high blast radius.
    Everything reversible is at most audited. The rule is intentionally
    simple: governance you cannot explain in one table is governance no
    one will trust.
    """
    r, b = profile.reversibility, profile.blast_radius

    if r is Reversibility.REVERSIBLE and b is BlastRadius.LOW:
        return Outcome.ALLOW
    if r is Reversibility.IRREVERSIBLE and b is BlastRadius.HIGH:
        return Outcome.REQUIRE_APPROVAL
    # the two mixed corners -> execute but keep a record
    return Outcome.ALLOW_WITH_AUDIT


@dataclass
class Decision:
    """A record of one governance decision, for the audit trail and the UI."""

    action: str
    reversibility: str
    blast_radius: str
    outcome: str
    reason: str
    approved: bool | None = None   # None until an approval outcome resolves
    arguments: dict = field(default_factory=dict)

    @classmethod
    def from_profile(cls, profile: ActionProfile, outcome: Outcome, arguments: dict | None = None) -> "Decision":
        reason = _explain(profile, outcome)
        return cls(
            action=profile.name,
            reversibility=profile.reversibility.value,
            blast_radius=profile.blast_radius.value,
            outcome=outcome.value,
            reason=reason,
            arguments=arguments or {},
        )


def _explain(profile: ActionProfile, outcome: Outcome) -> str:
    """A short, human-readable justification for a decision."""
    r = profile.reversibility.value
    b = profile.blast_radius.value
    if outcome is Outcome.ALLOW:
        return f"{r} action with {b} blast radius -> safe to auto-execute"
    if outcome is Outcome.ALLOW_WITH_AUDIT:
        return f"{r} action with {b} blast radius -> execute, but record for audit"
    return f"{r} action with {b} blast radius -> too consequential; a human must approve"
