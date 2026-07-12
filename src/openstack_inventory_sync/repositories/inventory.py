"""Inventory repository operations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from openstack_inventory_sync.models.mixins import OpenStackResourceMixin


@dataclass(frozen=True)
class InventoryWriteStats:
    fetched: int
    inserted: int
    updated: int
    unchanged: int
    deleted: int
    removed: int


class InventoryRepository:
    """Read and write inventory rows within a caller-owned transaction."""

    SYSTEM_FIELDS = {"created_at", "updated_at", "first_seen_at", "last_seen_at"}

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(
        self,
        model: type[OpenStackResourceMixin],
        payloads: Sequence[dict[str, Any]],
        *,
        region_name: str,
        seen_at: datetime,
        remove_missing: bool = False,
    ) -> InventoryWriteStats:
        inserted = 0
        updated = 0
        unchanged = 0
        seen_ids: set[str] = set()

        for payload in payloads:
            resource_id = str(payload["id"])
            seen_ids.add(resource_id)
            existing = self.session.get(model, resource_id)

            if existing is None:
                row = model(**payload)
                row.first_seen_at = seen_at
                row.last_seen_at = seen_at
                row.is_deleted = False
                row.deleted_at = None
                self.session.add(row)
                inserted += 1
                continue

            changed = False
            for key, value in payload.items():
                if key in self.SYSTEM_FIELDS:
                    continue
                if getattr(existing, key) != value:
                    setattr(existing, key, value)
                    changed = True

            if existing.is_deleted or existing.deleted_at is not None:
                existing.is_deleted = False
                existing.deleted_at = None
                changed = True

            existing.last_seen_at = seen_at
            if changed:
                updated += 1
            else:
                unchanged += 1

        deleted, removed = self._handle_missing(
            model=model,
            region_name=region_name,
            seen_ids=seen_ids,
            seen_at=seen_at,
            remove_missing=remove_missing,
        )
        return InventoryWriteStats(
            fetched=len(payloads),
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
            deleted=deleted,
            removed=removed,
        )

    def _handle_missing(
        self,
        *,
        model: type[OpenStackResourceMixin],
        region_name: str,
        seen_ids: set[str],
        seen_at: datetime,
        remove_missing: bool,
    ) -> tuple[int, int]:
        statement = select(model).where(
            model.region_name == region_name, model.is_deleted.is_(False)
        )
        if seen_ids:
            statement = statement.where(model.id.not_in(seen_ids))

        missing_rows = list(self.session.scalars(statement))
        if remove_missing:
            for row in missing_rows:
                self.session.delete(row)
            return 0, len(missing_rows)

        for row in missing_rows:
            row.is_deleted = True
            row.deleted_at = seen_at
            row.last_seen_at = seen_at
        return len(missing_rows), 0
