"""Demo tools spanning all four cells of the governance matrix.

These are toy implementations (they don't really touch a database or send
mail) but their *profiles* are realistic. The point of the demo is to watch
the same governance layer treat these four tools differently -- purely
because of where each one sits on the reversibility x blast-radius grid.
"""

from __future__ import annotations

from portcullis import BlastRadius, Policy, Reversibility


# --- the tool implementations (deliberately trivial) --------------------

def search_web(query: str) -> str:
    return f"top results for {query!r}: [3 articles found]"


def read_customer(customer_id: str) -> str:
    return f"customer {customer_id}: name=Acme Corp, status=active, plan=pro"


def send_email(to: str, subject: str) -> str:
    return f"email sent to {to} with subject {subject!r}"


def delete_customer(customer_id: str) -> str:
    return f"customer {customer_id} permanently deleted"


TOOLS = {
    "search_web": search_web,
    "read_customer": read_customer,
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
