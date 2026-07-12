from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session, sessionmaker

from openstack_inventory_sync.models import (
    Network,
    Port,
    SecurityGroup,
    SecurityGroupRule,
    Server,
    Subnet,
    Volume,
    VolumeAttachment,
)
from openstack_inventory_sync.repositories.inventory import InventoryRepository
from openstack_inventory_sync.sync.context import InventorySourceContext
from openstack_inventory_sync.sync.security_groups import SecurityGroupSync
from openstack_inventory_sync.sync.servers import ServerSync
from openstack_inventory_sync.sync.volumes import VolumeSync

SEEN_AT = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


def common_payload(resource_id: str, project_id: str, name: str) -> dict[str, object]:
    return {
        "id": resource_id,
        "region_name": "RegionOne",
        "name": name,
        "project_id": project_id,
        "status": "ACTIVE",
        "raw": {"id": resource_id, "name": name},
        "resource_created_at": None,
        "resource_updated_at": None,
    }


def test_source_specific_networks_subnets_and_ports(
    sqlite_session_factory: sessionmaker[Session],
    source_context: InventorySourceContext,
    other_source_context: InventorySourceContext,
) -> None:
    session = sqlite_session_factory()
    repository = InventoryRepository(session)

    for source, name in ((source_context, "appdev"), (other_source_context, "apptest")):
        repository.upsert_many(
            Network,
            [
                {
                    **common_payload("network-1", source.openstack_project_id, f"{name}-net"),
                    "mtu": 1500,
                    "admin_state_up": True,
                    "is_shared": False,
                    "is_router_external": False,
                    "provider_network_type": None,
                    "provider_physical_network": None,
                    "provider_segmentation_id": None,
                }
            ],
            source=source,
            seen_at=SEEN_AT,
        )
        repository.upsert_many(
            Subnet,
            [
                {
                    **common_payload("subnet-1", source.openstack_project_id, f"{name}-subnet"),
                    "network_id": "network-1",
                    "cidr": "10.0.0.0/24",
                    "ip_version": "4",
                    "gateway_ip": "10.0.0.1",
                    "enable_dhcp": True,
                    "allocation_pools": [],
                    "dns_nameservers": [],
                }
            ],
            source=source,
            seen_at=SEEN_AT,
        )
        repository.upsert_many(
            Port,
            [
                {
                    **common_payload("port-1", source.openstack_project_id, f"{name}-port"),
                    "network_id": "network-1",
                    "mac_address": "fa:16:3e:00:00:01",
                    "device_id": "server-1",
                    "device_owner": "compute:nova",
                    "fixed_ips": [],
                    "binding_host_id": "compute-01",
                    "admin_state_up": True,
                }
            ],
            source=source,
            seen_at=SEEN_AT,
        )
    session.flush()

    repository.upsert_many(Network, [], source=source_context, seen_at=SEEN_AT)
    session.flush()

    appdev_network = session.get(Network, (source_context.source_id, "network-1"))
    apptest_network = session.get(Network, (other_source_context.source_id, "network-1"))
    apptest_subnet = session.get(Subnet, (other_source_context.source_id, "subnet-1"))
    apptest_port = session.get(Port, (other_source_context.source_id, "port-1"))
    assert appdev_network is not None
    assert apptest_network is not None
    assert apptest_subnet is not None
    assert apptest_port is not None
    assert appdev_network.is_deleted is True
    assert apptest_network.is_deleted is False
    assert apptest_subnet.is_deleted is False
    assert apptest_port.is_deleted is False
    session.close()


class VolumeClient:
    def list_volumes(self) -> list[dict[str, object]]:
        return [
            {
                "id": "volume-1",
                "name": "root",
                "project_id": "project-appdev",
                "status": "available",
                "size": 20,
                "attachments": [
                    {
                        "attachment_id": "attachment-1",
                        "server_id": "server-1",
                        "device": "/dev/vda",
                    }
                ],
            }
        ]


def test_source_specific_volumes_and_attachments(
    sqlite_session_factory: sessionmaker[Session],
    source_context: InventorySourceContext,
) -> None:
    session = sqlite_session_factory()

    result = VolumeSync(VolumeClient(), source_context).run(session)
    session.flush()

    assert result.inserted == 1
    assert session.get(Volume, (source_context.source_id, "volume-1")) is not None
    assert (
        session.get(VolumeAttachment, (source_context.source_id, "volume-1", "attachment-1"))
        is not None
    )
    session.close()


class SecurityGroupClient:
    def list_security_groups(self) -> list[dict[str, object]]:
        return [
            {
                "id": "sg-1",
                "name": "web",
                "project_id": "project-appdev",
                "description": "web access",
                "security_group_rules": [
                    {
                        "id": "rule-1",
                        "direction": "ingress",
                        "ethertype": "IPv4",
                        "protocol": "tcp",
                        "port_range_min": 443,
                        "port_range_max": 443,
                        "remote_ip_prefix": "0.0.0.0/0",
                    }
                ],
            }
        ]


def test_source_specific_security_groups_and_rules(
    sqlite_session_factory: sessionmaker[Session],
    source_context: InventorySourceContext,
) -> None:
    session = sqlite_session_factory()

    result = SecurityGroupSync(SecurityGroupClient(), source_context).run(session)
    session.flush()

    assert result.inserted == 1
    assert session.get(SecurityGroup, (source_context.source_id, "sg-1")) is not None
    assert session.get(SecurityGroupRule, (source_context.source_id, "sg-1", "rule-1")) is not None
    session.close()


class FailingServerClient:
    def list_servers(self) -> list[dict[str, object]]:
        raise RuntimeError("OpenStack query failed")


def test_failed_openstack_query_does_not_deactivate_any_source(
    sqlite_session_factory: sessionmaker[Session],
    source_context: InventorySourceContext,
    other_source_context: InventorySourceContext,
) -> None:
    session = sqlite_session_factory()
    repository = InventoryRepository(session)

    for source in (source_context, other_source_context):
        repository.upsert_many(
            Server,
            [
                {
                    **common_payload("server-1", source.openstack_project_id, "web"),
                    "user_id": "user-1",
                    "flavor_id": "flavor-1",
                    "image_id": "image-1",
                    "availability_zone": "nova",
                    "compute_host": "compute-01",
                    "vm_state": "active",
                    "power_state": "1",
                    "addresses": {},
                    "metadata_json": {},
                    "launched_at": None,
                    "terminated_at": None,
                }
            ],
            source=source,
            seen_at=SEEN_AT,
        )
    session.flush()

    with pytest.raises(RuntimeError, match="OpenStack query failed"):
        ServerSync(FailingServerClient(), source_context).run(session)
    session.flush()

    appdev_server = session.get(Server, (source_context.source_id, "server-1"))
    apptest_server = session.get(Server, (other_source_context.source_id, "server-1"))
    assert appdev_server is not None
    assert apptest_server is not None
    assert appdev_server.is_deleted is False
    assert apptest_server.is_deleted is False
    session.close()
