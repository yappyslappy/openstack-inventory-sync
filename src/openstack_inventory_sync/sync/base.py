"""Base resource synchronization implementation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from openstack_inventory_sync.models.mixins import OpenStackResourceMixin
from openstack_inventory_sync.repositories.inventory import InventoryRepository
from openstack_inventory_sync.sync.context import InventorySourceContext
from openstack_inventory_sync.sync.result import SyncResult

logger = logging.getLogger(__name__)

Serializer = Callable[[Any, str], dict[str, Any]]
ResourcePayload = tuple[Any, dict[str, Any]]


class ResourceSync:
    """Synchronize one OpenStack resource type into one database table."""

    resource_name: str
    model: type[OpenStackResourceMixin]
    list_method_name: str
    serializer: Serializer
    enforce_project_id: bool = True
    shared_visibility_values: frozenset[str] = frozenset()

    def __init__(self, client: Any, source: InventorySourceContext) -> None:
        self.client = client
        self.source = source

    def fetch(self) -> list[Any]:
        method = getattr(self.client, self.list_method_name)
        return list(method())

    def run(self, session: Session, *, remove_missing: bool = False) -> SyncResult:
        started_at = datetime.now(UTC)
        logger.info(
            "resource_sync.started",
            extra={
                "resource": self.resource_name,
                "inventory_scope": self.source.scope_key,
                "openstack_project_id": self.source.openstack_project_id,
                "openstack_project_name": self.source.openstack_project_name,
            },
        )

        resources = self.fetch()
        accepted: list[ResourcePayload] = []
        rejected = 0
        for resource in resources:
            payload = self.serializer(resource, self.source.region_name)
            if self.reject_payload(payload):
                rejected += 1
                logger.warning(
                    "resource_sync.project_mismatch_skipped",
                    extra={
                        "resource": self.resource_name,
                        "inventory_scope": self.source.scope_key,
                        "openstack_project_id": self.source.openstack_project_id,
                        "resource_project_id": payload.get("project_id"),
                        "resource_id": payload.get("id"),
                    },
                )
                continue
            accepted.append((resource, payload))

        payloads = [payload for _, payload in accepted]
        repository = InventoryRepository(session)
        stats = repository.upsert_many(
            self.model,
            payloads,
            source=self.source,
            seen_at=started_at,
            remove_missing=remove_missing,
        )
        self.sync_child_records(repository, accepted)

        completed_at = datetime.now(UTC)
        result = SyncResult(
            resource=self.resource_name,
            inventory_scope=self.source.scope_key,
            openstack_project_id=self.source.openstack_project_id,
            openstack_project_name=self.source.openstack_project_name,
            started_at=started_at,
            completed_at=completed_at,
            fetched=len(resources),
            inserted=stats.inserted,
            updated=stats.updated,
            unchanged=stats.unchanged,
            deleted=stats.deleted,
            removed=stats.removed,
            rejected=rejected,
        )
        logger.info("resource_sync.completed", extra=result.as_log_dict())
        return result

    def reject_payload(self, payload: dict[str, Any]) -> bool:
        if not self.enforce_project_id:
            return False
        project_id = payload.get("project_id")
        if not project_id:
            return False
        if str(project_id) == self.source.openstack_project_id:
            return False
        visibility = payload.get("visibility")
        return visibility is None or str(visibility).lower() not in self.shared_visibility_values

    def sync_child_records(
        self, repository: InventoryRepository, accepted: list[ResourcePayload]
    ) -> None:
        return None
