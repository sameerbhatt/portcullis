"""Audit log: an append-only record of every governance decision.

Every decision the engine makes -- allowed, audited, approved, or denied --
is written here. In production this is your answer to "why did the agent do
that?"; in the demo it is what the web view renders live.

The log also supports observers: callables notified on each decision, so a
UI can stream decisions as they happen without polling a file.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .model import Decision

Observer = Callable[[Decision], None]


class AuditLog:
    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else None
        self._records: list[dict] = []
        self._observers: list[Observer] = []
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    def subscribe(self, observer: Observer) -> None:
        """Register a callback fired on every recorded decision."""
        self._observers.append(observer)

    def record(self, decision: Decision) -> None:
        entry = asdict(decision)
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._records.append(entry)
        if self._path:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        for obs in self._observers:
            obs(decision)

    @property
    def records(self) -> list[dict]:
        return list(self._records)

    def summary(self) -> dict[str, int]:
        """Counts by outcome -- handy for a one-line run summary."""
        counts: dict[str, int] = {}
        for r in self._records:
            key = r["outcome"] if r.get("approved") is not False else "denied"
            counts[key] = counts.get(key, 0) + 1
        return counts
