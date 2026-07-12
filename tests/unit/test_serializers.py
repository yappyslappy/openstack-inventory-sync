from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from openstack_inventory_sync.openstack.serializers import (
    parse_datetime,
    serialize_network,
    serialize_server,
    serialize_volume,
)


def test_serialize_server_normalizes_nested_ids_and_dates() -> None:
    payload = serialize_server(
        {
            "id": "server-1",
            "name": "web-01",
            "project_id": "project-1",
            "status": "ACTIVE",
            "created_at": "2026-07-12T12:00:00Z",
            "updated_at": "2026-07-12T12:30:00+00:00",
            "image": {"id": "image-1"},
            "flavor": {"id": "flavor-1"},
            "metadata": {"role": "web"},
            "addresses": {"private": [{"addr": "10.0.0.10"}]},
            "OS-EXT-AZ:availability_zone": "nova",
            "OS-EXT-SRV-ATTR:host": "compute-01",
            "OS-EXT-STS:vm_state": "active",
            "OS-EXT-STS:power_state": 1,
            "OS-SRV-USG:launched_at": "2026-07-12T12:01:00Z",
        },
        "RegionOne",
    )

    assert payload["id"] == "server-1"
    assert payload["image_id"] == "image-1"
    assert payload["flavor_id"] == "flavor-1"
    assert payload["availability_zone"] == "nova"
    assert payload["power_state"] == "1"
    assert payload["resource_created_at"] == datetime(2026, 7, 12, 12, 0, tzinfo=UTC)
    assert payload["raw"]["created_at"] == "2026-07-12T12:00:00Z"


def test_serialize_network_handles_provider_keys() -> None:
    payload = serialize_network(
        {
            "id": "network-1",
            "name": "public",
            "router:external": True,
            "provider:network_type": "vlan",
            "provider:physical_network": "physnet1",
            "provider:segmentation_id": 123,
        },
        "RegionOne",
    )

    assert payload["is_router_external"] is True
    assert payload["provider_network_type"] == "vlan"
    assert payload["provider_segmentation_id"] == 123


def test_serialize_volume_converts_bootable_string() -> None:
    payload = serialize_volume(
        SimpleNamespace(id="volume-1", name="root", size=20, bootable="true"),
        "RegionOne",
    )

    assert payload["bootable"] is True
    assert payload["size_gb"] == 20


def test_parse_datetime_returns_none_for_unparseable_values() -> None:
    assert parse_datetime("not a date") is None
