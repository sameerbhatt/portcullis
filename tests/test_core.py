"""Tests for the framework-agnostic core. No API key, no network, no LLM."""

import pytest

from portcullis import (
    ActionDenied,
    AuditLog,
    AutoApprove,
    BlastRadius,
    GovernanceEngine,
    Outcome,
    Policy,
    Reversibility,
    decide,
)
from portcullis.core.model import ActionProfile


def profile(rev, blast):
    return ActionProfile(name="t", reversibility=rev, blast_radius=blast)


def test_decision_matrix_all_four_cells():
    assert decide(profile(Reversibility.REVERSIBLE, BlastRadius.LOW)) is Outcome.ALLOW
    assert decide(profile(Reversibility.REVERSIBLE, BlastRadius.HIGH)) is Outcome.ALLOW_WITH_AUDIT
    assert decide(profile(Reversibility.IRREVERSIBLE, BlastRadius.LOW)) is Outcome.ALLOW_WITH_AUDIT
    assert decide(profile(Reversibility.IRREVERSIBLE, BlastRadius.HIGH)) is Outcome.REQUIRE_APPROVAL


def test_only_one_cell_pauses():
    outcomes = [
        decide(profile(r, b))
        for r in Reversibility
        for b in BlastRadius
    ]
    assert outcomes.count(Outcome.REQUIRE_APPROVAL) == 1


def test_policy_fail_closed_treats_unknown_as_most_dangerous():
    p = Policy(fail_closed=True)
    prof = p.profile_for("never_declared")
    assert prof.reversibility is Reversibility.IRREVERSIBLE
    assert prof.blast_radius is BlastRadius.HIGH
    assert decide(prof) is Outcome.REQUIRE_APPROVAL


def test_policy_fail_open_treats_unknown_as_safe():
    p = Policy(fail_closed=False)
    assert decide(p.profile_for("x")) is Outcome.ALLOW


def test_engine_allows_reversible_low():
    p = Policy().register("read", Reversibility.REVERSIBLE, BlastRadius.LOW)
    engine = GovernanceEngine(p)
    result = engine.guard("read", lambda: "data")
    assert result == "data"


def test_engine_pauses_and_denies_without_approval():
    p = Policy().register("delete", Reversibility.IRREVERSIBLE, BlastRadius.HIGH)
    engine = GovernanceEngine(p, approval=AutoApprove(approve=False))
    called = []
    with pytest.raises(ActionDenied):
        engine.guard("delete", lambda: called.append(True))
    assert called == []  # the real function never ran


def test_engine_executes_when_approved():
    p = Policy().register("email", Reversibility.IRREVERSIBLE, BlastRadius.HIGH)
    engine = GovernanceEngine(p, approval=AutoApprove(approve=True))
    result = engine.guard("email", lambda to: f"sent to {to}", "a@b.com")
    assert result == "sent to a@b.com"


def test_audit_records_every_decision():
    audit = AuditLog()
    p = (
        Policy()
        .register("read", Reversibility.REVERSIBLE, BlastRadius.LOW)
        .register("wipe", Reversibility.IRREVERSIBLE, BlastRadius.HIGH)
    )
    engine = GovernanceEngine(p, approval=AutoApprove(approve=True), audit=audit)
    engine.guard("read", lambda: 1)
    engine.guard("wipe", lambda: 2)
    assert len(audit.records) == 2
    assert audit.records[0]["outcome"] == "allow"
    assert audit.records[1]["outcome"] == "require_approval"


def test_arguments_captured_in_decision():
    p = Policy().register("send", Reversibility.IRREVERSIBLE, BlastRadius.HIGH)
    engine = GovernanceEngine(p)
    decision = engine.evaluate("send", arguments={"to": "x@y.com"})
    assert decision.arguments == {"to": "x@y.com"}
    assert decision.outcome == "require_approval"
