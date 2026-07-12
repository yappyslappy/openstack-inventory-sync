"""Inventory repository operations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from openstack_inventory_sync.exceptions import InventorySourceConflictError
from openstack_inventory_sync.models import InventorySource
from openstack_inventory_sync.models.mixins import OpenStackResourceMixin
from openstack_inventory_sync.sync.context import InventorySourceContext


@dataclass(frozen=True)
class InventoryWriteStats:
    fetched: int
    inserted: int
    updated: int
    unchanged: int
    deleted: int
    removed: int


@dataclass(frozen=True)
class InventorySourceUpsert:
    context: InventorySourceContext
    created: bool


class InventoryRepository:
    """Read and write inventory rows within a caller-owned transaction."""

    SYSTEM_FIELDS = {"created_at", "updated_at", "first_seen_at", "last_seen_at"}

    def __init__(self, session: Session) -> None:
        self.session = session

    def validate_inventory_source_mapping(
        self,
        *,
        scope_key: str,
        openstack_project_id: str,
        region_name: str,
        auth_url: str,
    ) -> None:
        existing_by_scope, existing_by_mapping = self._find_source_rows(
            scope_key=scope_key,
            openstack_project_id=openstack_project_id,
            region_name=region_name,
            auth_url=auth_url,
        )
        self._validate_source_rows(
            existing_by_scope=existing_by_scope,
            existing_by_mapping=existing_by_mapping,
            scope_key=scope_key,
            openstack_project_id=openstack_project_id,
            region_name=region_name,
            auth_url=auth_url,
        )

    def ensure_inventory_source(
        self,
        *,
        scope_key: str,
        openstack_project_id: str,
        openstack_project_name: str,
        region_name: str,
        auth_url: str,
    ) -> InventorySourceUpsert:
        existing_by_scope, existing_by_mapping = self._find_source_rows(
            scope_key=scope_key,
            openstack_project_id=openstack_project_id,
            region_name=region_name,
            auth_url=auth_url,
        )
        self._validate_source_rows(
            existing_by_scope=existing_by_scope,
            existing_by_mapping=existing_by_mapping,
            scope_key=scope_key,
            openstack_project_id=openstack_project_id,
            region_name=region_name,
            auth_url=auth_url,
        )

        source = existing_by_scope or existing_by_mapping
        created = source is None

        if source is None:
            source = InventorySource(
                scope_key=scope_key,
                openstack_project_id=openstack_project_id,
                openstack_project_name=openstack_project_name,
                region_name=region_name,
                auth_url=auth_url,
                is_active=True,
            )
            self.session.add(source)
            self.session.flush()
        else:
            if source.scope_key != scope_key:
                raise InventorySourceConflictError(
                    "OPENSTACK_PROJECT_ID is already associated with a different INVENTORY_SCOPE"
                )
            if (
                source.openstack_project_id != openstack_project_id
                or source.region_name != region_name
                or source.auth_url != auth_url
            ):
                raise InventorySourceConflictError(
                    "INVENTORY_SCOPE is already associated with different OpenStack metadata"
                )
            source.openstack_project_name = openstack_project_name
            source.is_active = True

        return InventorySourceUpsert(context=self._context_from_source(source), created=created)

    def _find_source_rows(
        self,
        *,
        scope_key: str,
        openstack_project_id: str,
        region_name: str,
        auth_url: str,
    ) -> tuple[InventorySource | None, InventorySource | None]:
        existing_by_scope = self.session.scalars(
            select(InventorySource).where(InventorySource.scope_key == scope_key)
        ).one_or_none()
        existing_by_mapping = self.session.scalars(
            select(InventorySource).where(
                InventorySource.auth_url == auth_url,
                InventorySource.region_name == region_name,
                InventorySource.openstack_project_id == openstack_project_id,
            )
        ).one_or_none()
        return existing_by_scope, existing_by_mapping

    def _validate_source_rows(
        self,
        *,
        existing_by_scope: InventorySource | None,
        existing_by_mapping: InventorySource | None,
        scope_key: str,
        openstack_project_id: str,
        region_name: str,
        auth_url: str,
    ) -> None:
        if (
            existing_by_scope is not None
            and existing_by_mapping is not None
            and existing_by_scope.id != existing_by_mapping.id
        ):
            raise InventorySourceConflictError(
                "INVENTORY_SCOPE and OPENSTACK_PROJECT_ID map to different inventory sources"
            )
        if existing_by_scope is not None and (
            existing_by_scope.openstack_project_id != openstack_project_id
            or existing_by_scope.region_name != region_name
            or existing_by_scope.auth_url != auth_url
        ):
            raise InventorySourceConflictError(
                "INVENTORY_SCOPE is already associated with different OpenStack metadata"
            )
        if existing_by_mapping is not None and existing_by_mapping.scope_key != scope_key:
            raise InventorySourceConflictError(
                "OPENSTACK_PROJECT_ID is already associated with a different INVENTORY_SCOPE"
            )

    def mark_source_success(self, source: InventorySourceContext) -> None:
        row = self.session.get(InventorySource, source.source_id)
        if row is None:
            raise InventorySourceConflictError("Inventory source disappeared during sync")
        row.last_successful_sync_at = datetime.now(UTC)
        row.is_active = True

    def mark_source_failure(self, source: InventorySourceContext) -> None:
        row = self.session.get(InventorySource, source.source_id)
        if row is None:
            raise InventorySourceConflictError("Inventory source disappeared during sync")
        row.last_failed_sync_at = datetime.now(UTC)

    def upsert_many(
        self,
        model: type[OpenStackResourceMixin],
        payloads: Sequence[dict[str, Any]],
        *,
        source: InventorySourceContext,
        seen_at: datetime,
        remove_missing: bool = False,
    ) -> InventoryWriteStats:
        self._require_source(source)
        inserted = 0
        updated = 0
        unchanged = 0
        seen_ids: set[str] = set()

        for payload in payloads:
            resource_id = str(payload["id"])
            seen_ids.add(resource_id)
            existing = self.session.scalars(
                select(model).where(
                    model.inventory_source_id == source.source_id,
                    model.id == resource_id,
                )
            ).one_or_none()
            payload = {**payload, "inventory_source_id": source.source_id}

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
            source=source,
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
        source: InventorySourceContext,
        seen_ids: set[str],
        seen_at: datetime,
        remove_missing: bool,
    ) -> tuple[int, int]:
        self._require_source(source)
        statement = select(model).where(
            model.inventory_source_id == source.source_id,
            model.region_name == source.region_name,
            model.is_deleted.is_(False),
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

    def replace_child_records(
        self,
        model: type[Any],
        payloads: Sequence[dict[str, Any]],
        *,
        source: InventorySourceContext,
        parent_field: str,
        parent_ids: set[str],
    ) -> int:
        self._require_source(source)
        if not parent_ids:
            return 0
        parent_column = getattr(model, parent_field)
        self.session.execute(
            delete(model).where(
                model.inventory_source_id == source.source_id,
                parent_column.in_(parent_ids),
            )
        )
        for payload in payloads:
            self.session.add(model(**payload, inventory_source_id=source.source_id))
        return len(payloads)

    def _context_from_source(self, source: InventorySource) -> InventorySourceContext:
        return InventorySourceContext(
            source_id=source.id,
            scope_key=source.scope_key,
            openstack_project_id=source.openstack_project_id,
            openstack_project_name=source.openstack_project_name,
            region_name=source.region_name,
            auth_url=source.auth_url,
        )

    def _require_source(self, source: InventorySourceContext | None) -> None:
        if source is None or source.source_id <= 0 or not source.scope_key:
            raise InventorySourceConflictError(
                "Project-scoped inventory operation requires an inventory source context"
            )
