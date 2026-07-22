"""Policy: the declared mapping from a tool to its governance profile.

In the MVP, reversibility and blast radius are *declared*, not inferred.
That is a deliberate choice: a governance layer whose classifications you
cannot see and edit is not one you can trust in production. Auto-inference
(an LLM proposing the profile, a human confirming it) is a v2 feature and
is named as such in the README, not left as an accidental gap.
"""

from __future__ import annotations

from .model import ActionProfile, BlastRadius, Reversibility


class Policy:
    """A registry of action profiles, keyed by tool name.

    Fail-closed: if a tool has no declared profile, it is treated as the
    most dangerous cell (irreversible + high) so that unknown actions pause
    for a human rather than slipping through. Governance should be safe by
    default, not permissive by default.
    """

    def __init__(self, fail_closed: bool = True) -> None:
        self._profiles: dict[str, ActionProfile] = {}
        self._fail_closed = fail_closed

    def register(
        self,
        name: str,
        reversibility: Reversibility,
        blast_radius: BlastRadius,
        description: str = "",
    ) -> "Policy":
        """Declare the governance profile for a tool. Chainable."""
        self._profiles[name] = ActionProfile(
            name=name,
            reversibility=reversibility,
            blast_radius=blast_radius,
            description=description,
        )
        return self

    def profile_for(self, name: str) -> ActionProfile:
        if name in self._profiles:
            return self._profiles[name]
        if self._fail_closed:
            return ActionProfile(
                name=name,
                reversibility=Reversibility.IRREVERSIBLE,
                blast_radius=BlastRadius.HIGH,
                description="undeclared tool (fail-closed default)",
            )
        return ActionProfile(
            name=name,
            reversibility=Reversibility.REVERSIBLE,
            blast_radius=BlastRadius.LOW,
            description="undeclared tool (fail-open default)",
        )

    def known(self, name: str) -> bool:
        return name in self._profiles

    def __len__(self) -> int:
        return len(self._profiles)
