"""Synchronization result types."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SyncResult:
    resource: str
    inventory_scope: str
    openstack_project_id: str
    openstack_project_name: str
    started_at: datetime
    completed_at: datetime
    fetched: int
    inserted: int
    updated: int
    unchanged: int
    deleted: int
    removed: int
    rejected: int

    @property
    def duration_seconds(self) -> float:
        return round((self.completed_at - self.started_at).total_seconds(), 6)

    def as_log_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["started_at"] = self.started_at.isoformat()
        payload["completed_at"] = self.completed_at.isoformat()
        payload["duration_seconds"] = self.duration_seconds
        return payload
