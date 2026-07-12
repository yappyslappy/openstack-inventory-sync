"""Synchronization orchestration."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from openstack_inventory_sync.database.session import transactional_session
from openstack_inventory_sync.exceptions import SyncError
from openstack_inventory_sync.sync.base import ResourceSync
from openstack_inventory_sync.sync.flavors import FlavorSync
from openstack_inventory_sync.sync.floating_ips import FloatingIPSync
from openstack_inventory_sync.sync.images import ImageSync
from openstack_inventory_sync.sync.networks import NetworkSync
from openstack_inventory_sync.sync.ports import PortSync
from openstack_inventory_sync.sync.projects import ProjectSync
from openstack_inventory_sync.sync.result import SyncResult
from openstack_inventory_sync.sync.security_groups import SecurityGroupSync
from openstack_inventory_sync.sync.servers import ServerSync
from openstack_inventory_sync.sync.subnets import SubnetSync
from openstack_inventory_sync.sync.volumes import VolumeSync

logger = logging.getLogger(__name__)

SYNC_CLASSES: tuple[type[ResourceSync], ...] = (
    ProjectSync,
    FlavorSync,
    ImageSync,
    NetworkSync,
    SubnetSync,
    SecurityGroupSync,
    PortSync,
    ServerSync,
    VolumeSync,
    FloatingIPSync,
)


class SyncOrchestrator:
    """Run full or resource-specific synchronization workflows."""

    def __init__(
        self, client: Any, session_factory: sessionmaker[Session], region_name: str
    ) -> None:
        self.session_factory = session_factory
        self.syncs = {
            sync_class.resource_name: sync_class(client, region_name) for sync_class in SYNC_CLASSES
        }

    @property
    def resource_names(self) -> tuple[str, ...]:
        return tuple(self.syncs.keys())

    def sync_all(self, *, remove_missing: bool = False) -> list[SyncResult]:
        return self.sync_resources(self.resource_names, remove_missing=remove_missing)

    def sync_resource(self, resource_name: str, *, remove_missing: bool = False) -> SyncResult:
        return self.sync_resources((resource_name,), remove_missing=remove_missing)[0]

    def sync_resources(
        self, resource_names: tuple[str, ...], *, remove_missing: bool = False
    ) -> list[SyncResult]:
        unknown = sorted(set(resource_names) - set(self.syncs))
        if unknown:
            raise SyncError(f"Unsupported resource type: {', '.join(unknown)}")

        results: list[SyncResult] = []
        logger.info("sync_run.started", extra={"resources": list(resource_names)})
        for resource_name in resource_names:
            sync = self.syncs[resource_name]
            try:
                with transactional_session(self.session_factory) as session:
                    results.append(sync.run(session, remove_missing=remove_missing))
            except Exception:
                logger.error("sync_run.resource_failed", extra={"resource": resource_name})
                raise SyncError(f"Failed to synchronize resource type: {resource_name}") from None

        logger.info(
            "sync_run.completed",
            extra={"resources": [result.as_log_dict() for result in results]},
        )
        return results
