"""Normalize OpenStack SDK resources into ORM payloads."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any


def serialize_project(resource: Any, region_name: str) -> dict[str, Any]:
    data = resource_to_dict(resource)
    return {
        **base_payload(resource, data, region_name),
        "domain_id": value(resource, data, "domain_id", "domain_id"),
        "description": value(resource, data, "description"),
        "enabled": value(resource, data, "enabled", "is_enabled"),
    }


def serialize_flavor(resource: Any, region_name: str) -> dict[str, Any]:
    data = resource_to_dict(resource)
    return {
        **base_payload(resource, data, region_name),
        "vcpus": value(resource, data, "vcpus"),
        "ram_mb": value(resource, data, "ram"),
        "disk_gb": value(resource, data, "disk"),
        "ephemeral_gb": value(resource, data, "ephemeral"),
        "swap_mb": value(resource, data, "swap"),
        "is_public": value(resource, data, "is_public"),
    }


def serialize_image(resource: Any, region_name: str) -> dict[str, Any]:
    data = resource_to_dict(resource)
    return {
        **base_payload(resource, data, region_name),
        "visibility": value(resource, data, "visibility"),
        "container_format": value(resource, data, "container_format"),
        "disk_format": value(resource, data, "disk_format"),
        "min_disk": value(resource, data, "min_disk"),
        "min_ram": value(resource, data, "min_ram"),
        "size_bytes": value(resource, data, "size"),
        "checksum": value(resource, data, "checksum"),
    }


def serialize_network(resource: Any, region_name: str) -> dict[str, Any]:
    data = resource_to_dict(resource)
    return {
        **base_payload(resource, data, region_name),
        "mtu": value(resource, data, "mtu"),
        "admin_state_up": value(resource, data, "admin_state_up", "is_admin_state_up"),
        "is_shared": value(resource, data, "is_shared", "shared"),
        "is_router_external": value(
            resource,
            data,
            "is_router_external",
            "router:external",
            "provider_router_external",
        ),
        "provider_network_type": value(
            resource,
            data,
            "provider_network_type",
            "provider:network_type",
        ),
        "provider_physical_network": value(
            resource,
            data,
            "provider_physical_network",
            "provider:physical_network",
        ),
        "provider_segmentation_id": value(
            resource,
            data,
            "provider_segmentation_id",
            "provider:segmentation_id",
        ),
    }


def serialize_subnet(resource: Any, region_name: str) -> dict[str, Any]:
    data = resource_to_dict(resource)
    return {
        **base_payload(resource, data, region_name),
        "network_id": value(resource, data, "network_id"),
        "cidr": value(resource, data, "cidr"),
        "ip_version": as_string(value(resource, data, "ip_version")),
        "gateway_ip": value(resource, data, "gateway_ip"),
        "enable_dhcp": value(resource, data, "enable_dhcp", "is_dhcp_enabled"),
        "allocation_pools": value(resource, data, "allocation_pools"),
        "dns_nameservers": value(resource, data, "dns_nameservers"),
    }


def serialize_port(resource: Any, region_name: str) -> dict[str, Any]:
    data = resource_to_dict(resource)
    return {
        **base_payload(resource, data, region_name),
        "network_id": value(resource, data, "network_id"),
        "mac_address": value(resource, data, "mac_address"),
        "device_id": value(resource, data, "device_id"),
        "device_owner": value(resource, data, "device_owner"),
        "fixed_ips": value(resource, data, "fixed_ips"),
        "binding_host_id": value(resource, data, "binding_host_id", "binding:host_id"),
        "admin_state_up": value(resource, data, "admin_state_up", "is_admin_state_up"),
    }


def serialize_server(resource: Any, region_name: str) -> dict[str, Any]:
    data = resource_to_dict(resource)
    image = value(resource, data, "image") or {}
    flavor = value(resource, data, "flavor") or {}
    return {
        **base_payload(resource, data, region_name),
        "user_id": value(resource, data, "user_id"),
        "flavor_id": extract_nested_id(flavor),
        "image_id": extract_nested_id(image),
        "availability_zone": value(
            resource,
            data,
            "availability_zone",
            "OS-EXT-AZ:availability_zone",
        ),
        "compute_host": value(resource, data, "hypervisor_hostname", "OS-EXT-SRV-ATTR:host"),
        "vm_state": value(resource, data, "vm_state", "OS-EXT-STS:vm_state"),
        "power_state": as_string(value(resource, data, "power_state", "OS-EXT-STS:power_state")),
        "addresses": value(resource, data, "addresses"),
        "metadata_json": value(resource, data, "metadata"),
        "launched_at": parse_datetime(
            value(resource, data, "launched_at", "OS-SRV-USG:launched_at")
        ),
        "terminated_at": parse_datetime(
            value(resource, data, "terminated_at", "OS-SRV-USG:terminated_at")
        ),
    }


def serialize_volume(resource: Any, region_name: str) -> dict[str, Any]:
    data = resource_to_dict(resource)
    return {
        **base_payload(resource, data, region_name),
        "size_gb": value(resource, data, "size"),
        "volume_type": value(resource, data, "volume_type"),
        "bootable": as_bool(value(resource, data, "bootable")),
        "availability_zone": value(resource, data, "availability_zone"),
        "attachments": value(resource, data, "attachments"),
    }


def serialize_floating_ip(resource: Any, region_name: str) -> dict[str, Any]:
    data = resource_to_dict(resource)
    return {
        **base_payload(resource, data, region_name),
        "floating_ip_address": value(resource, data, "floating_ip_address"),
        "fixed_ip_address": value(resource, data, "fixed_ip_address"),
        "port_id": value(resource, data, "port_id"),
        "router_id": value(resource, data, "router_id"),
        "network_id": value(resource, data, "floating_network_id", "network_id"),
    }


def serialize_security_group(resource: Any, region_name: str) -> dict[str, Any]:
    data = resource_to_dict(resource)
    return {
        **base_payload(resource, data, region_name),
        "description": value(resource, data, "description"),
        "security_group_rules": value(resource, data, "security_group_rules", "rules"),
    }


def base_payload(resource: Any, data: Mapping[str, Any], region_name: str) -> dict[str, Any]:
    openstack_id = value(resource, data, "id")
    if openstack_id is None or str(openstack_id).strip() == "":
        raise ValueError("OpenStack resource is missing an id")

    return {
        "id": str(openstack_id),
        "region_name": region_name,
        "name": value(resource, data, "name"),
        "project_id": value(resource, data, "project_id", "tenant_id"),
        "status": as_string(value(resource, data, "status")),
        "resource_created_at": parse_datetime(value(resource, data, "created_at", "created")),
        "resource_updated_at": parse_datetime(value(resource, data, "updated_at", "updated")),
        "raw": json_safe(data),
    }


def resource_to_dict(resource: Any) -> dict[str, Any]:
    if isinstance(resource, Mapping):
        return dict(resource)
    if hasattr(resource, "to_dict"):
        to_dict = resource.to_dict
        for kwargs in (
            {"computed": False},
            {"body": True, "headers": False, "computed": False},
            {},
        ):
            try:
                data = to_dict(**kwargs)
            except TypeError:
                continue
            if isinstance(data, Mapping):
                return dict(data)
    if hasattr(resource, "__dict__"):
        return {
            key: item
            for key, item in vars(resource).items()
            if not key.startswith("_") and not callable(item)
        }
    return {}


def value(resource: Any, data: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in data:
            return data[name]
        safe_name = name.replace(":", "_").replace("-", "_")
        if safe_name in data:
            return data[safe_name]
        if hasattr(resource, safe_name):
            return getattr(resource, safe_name)
        if hasattr(resource, name):
            return getattr(resource, name)
    return None


def extract_nested_id(value_: Any) -> str | None:
    if value_ is None:
        return None
    if isinstance(value_, Mapping):
        nested = value_.get("id")
        return str(nested) if nested is not None else None
    if hasattr(value_, "id"):
        nested = value_.id
        return str(nested) if nested is not None else None
    return str(value_)


def parse_datetime(value_: Any) -> datetime | None:
    if value_ is None or value_ == "":
        return None
    if isinstance(value_, datetime):
        return value_ if value_.tzinfo else value_.replace(tzinfo=UTC)
    if isinstance(value_, str):
        normalized = value_.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def as_bool(value_: Any) -> bool | None:
    if value_ is None:
        return None
    if isinstance(value_, bool):
        return value_
    if isinstance(value_, str):
        lowered = value_.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return bool(value_)


def as_string(value_: Any) -> str | None:
    if value_ is None:
        return None
    return str(value_)


def json_safe(value_: Any) -> Any:
    if isinstance(value_, datetime):
        return value_.isoformat()
    if isinstance(value_, Mapping):
        return {str(key): json_safe(item) for key, item in value_.items()}
    if isinstance(value_, Iterable) and not isinstance(value_, str | bytes | bytearray):
        return [json_safe(item) for item in value_]
    if isinstance(value_, str | int | float | bool) or value_ is None:
        return value_
    return str(value_)
