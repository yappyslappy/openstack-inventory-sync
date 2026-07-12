"""Base resource synchronization implementation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from openstack_inventory_sync.models.mixins import OpenStackResourceMixin
from openstack_inventory_sync.repositories.inventory import InventoryRepository
from openstack_inventory_sync.sync.result import SyncResult

logger = logging.getLogger(__name__)

Serializer = Callable[[Any, str], dict[str, Any]]


class ResourceSync:
    """Synchronize one OpenStack resource type into one database table."""

    resource_name: str
    model: type[OpenStackResourceMixin]
    list_method_name: str
    serializer: Serializer

    def __init__(self, client: Any, region_name: str) -> None:
        self.client = client
        self.region_name = region_name

    def fetch(self) -> list[Any]:
        method = getattr(self.client, self.list_method_name)
        return list(method())

    def run(self, session: Session, *, remove_missing: bool = False) -> SyncResult:
        started_at = datetime.now(UTC)
        logger.info("resource_sync.started", extra={"resource": self.resource_name})

        resources = self.fetch()
        payloads = [self.serializer(resource, self.region_name) for resource in resources]
        repository = InventoryRepository(session)
        stats = repository.upsert_many(
            self.model,
            payloads,
            region_name=self.region_name,
            seen_at=started_at,
            remove_missing=remove_missing,
        )

        completed_at = datetime.now(UTC)
        result = SyncResult(
            resource=self.resource_name,
            started_at=started_at,
            completed_at=completed_at,
            fetched=stats.fetched,
            inserted=stats.inserted,
            updated=stats.updated,
            unchanged=stats.unchanged,
            deleted=stats.deleted,
            removed=stats.removed,
        )
        logger.info("resource_sync.completed", extra=result.as_log_dict())
        return result
