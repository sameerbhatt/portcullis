"""Demo tools spanning all four cells of the governance matrix.

These are toy implementations (they don't really touch a database or send
mail) but their *profiles* are realistic. The point of the demo is to watch
the same governance layer treat these six tools differently -- purely
because of where each one sits on the reversibility x blast-radius grid.

Two of them exist specifically to occupy the mixed cells, which are the
easiest ones to overlook: an action can be reversible and still reach far
enough to deserve a record (`retag_open_tickets`), and an action can touch a
single row and still be impossible to undo (`write_audit_note`). Neither
stops the agent; both leave a trail.
"""

from __future__ import annotations

from portcullis import BlastRadius, Policy, Reversibility


# --- the tool implementations (deliberately trivial) --------------------

def search_web(query: str) -> str:
    return f"top results for {query!r}: [3 articles found]"


def read_customer(customer_id: str) -> str:
    return f"customer {customer_id}: name=Acme Corp, status=active, plan=pro"


def write_audit_note(customer_id: str, note: str) -> str:
    return f"note appended to the immutable ledger for {customer_id}: {note!r}"


def retag_open_tickets(tag: str) -> str:
    return f"tag {tag!r} applied to all 143 open tickets"


def send_email(to: str, subject: str) -> str:
    return f"email sent to {to} with subject {subject!r}"


def delete_customer(customer_id: str) -> str:
    return f"customer {customer_id} permanently deleted"


TOOLS = {
    "search_web": search_web,
    "read_customer": read_customer,
    "write_audit_note": write_audit_note,
    "retag_open_tickets": retag_open_tickets,
    "send_email": send_email,
    "delete_customer": delete_customer,
}


# --- the declared policy ------------------------------------------------

def build_policy() -> Policy:
    """One place that declares the governance profile of every tool."""
    return (
        Policy(fail_closed=True)
        .register(
            "search_web",
            Reversibility.REVERSIBLE, BlastRadius.LOW,
            "read-only public search; nothing changes",
        )
        .register(
            "read_customer",
            Reversibility.REVERSIBLE, BlastRadius.LOW,
            "reads one internal record; no side effects",
        )
        .register(
            "write_audit_note",
            Reversibility.IRREVERSIBLE, BlastRadius.LOW,
            "append-only ledger entry; cannot be edited away, but touches one record",
        )
        .register(
            "retag_open_tickets",
            Reversibility.REVERSIBLE, BlastRadius.HIGH,
            "tags can be removed, but this writes across the whole open queue",
        )
        .register(
            "send_email",
            Reversibility.IRREVERSIBLE, BlastRadius.HIGH,
            "contacts an external party; cannot be unsent",
        )
        .register(
            "delete_customer",
            Reversibility.IRREVERSIBLE, BlastRadius.HIGH,
            "destroys a production record; irreversible",
        )
    )
