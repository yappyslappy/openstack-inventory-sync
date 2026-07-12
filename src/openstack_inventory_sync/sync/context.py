"""Synchronization source context."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InventorySourceContext:
    """Identity and safety context for one OpenStack project source."""

    source_id: int
    scope_key: str
    openstack_project_id: str
    openstack_project_name: str
    region_name: str
    auth_url: str
