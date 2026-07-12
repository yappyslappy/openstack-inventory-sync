"""Subnet inventory model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.models.mixins import OpenStackResourceMixin


class Subnet(OpenStackResourceMixin, Base):
    __tablename__ = "subnets"

    network_id: Mapped[str | None] = mapped_column(String(128), index=True)
    cidr: Mapped[str | None] = mapped_column(String(64), index=True)
    ip_version: Mapped[str | None] = mapped_column(String(16), index=True)
    gateway_ip: Mapped[str | None] = mapped_column(String(64))
    enable_dhcp: Mapped[bool | None] = mapped_column(Boolean)
    allocation_pools: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    dns_nameservers: Mapped[list[str] | None] = mapped_column(JSON)
