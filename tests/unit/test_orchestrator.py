from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from openstack_inventory_sync.exceptions import SyncError
from openstack_inventory_sync.sync.orchestrator import SyncOrchestrator


class EmptyClient:
    def list_projects(self) -> list[object]:
        return []

    def list_flavors(self) -> list[object]:
        return []

    def list_images(self) -> list[object]:
        return []

    def list_networks(self) -> list[object]:
        return []

    def list_subnets(self) -> list[object]:
        return []

    def list_ports(self) -> list[object]:
        return []

    def list_servers(self) -> list[object]:
        return []

    def list_volumes(self) -> list[object]:
        return []

    def list_floating_ips(self) -> list[object]:
        return []

    def list_security_groups(self) -> list[object]:
        return []


def test_orchestrator_supports_resource_specific_sync(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    orchestrator = SyncOrchestrator(EmptyClient(), sqlite_session_factory, "RegionOne")

    result = orchestrator.sync_resource("servers")

    assert result.resource == "servers"
    assert result.fetched == 0


def test_orchestrator_rejects_unknown_resource(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    orchestrator = SyncOrchestrator(EmptyClient(), sqlite_session_factory, "RegionOne")

    with pytest.raises(SyncError, match="Unsupported resource"):
        orchestrator.sync_resource("not-real")
