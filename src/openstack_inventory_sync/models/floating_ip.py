"""Floating IP inventory model."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.models.mixins import OpenStackResourceMixin


class FloatingIP(OpenStackResourceMixin, Base):
    __tablename__ = "floating_ips"

    floating_ip_address: Mapped[str | None] = mapped_column(String(64), index=True)
    fixed_ip_address: Mapped[str | None] = mapped_column(String(64), index=True)
    port_id: Mapped[str | None] = mapped_column(String(128), index=True)
    router_id: Mapped[str | None] = mapped_column(String(128), index=True)
    network_id: Mapped[str | None] = mapped_column(String(128), index=True)
