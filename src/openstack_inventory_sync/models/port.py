"""Port inventory model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.models.mixins import OpenStackResourceMixin


class Port(OpenStackResourceMixin, Base):
    __tablename__ = "ports"

    network_id: Mapped[str | None] = mapped_column(String(128), index=True)
    mac_address: Mapped[str | None] = mapped_column(String(64), index=True)
    device_id: Mapped[str | None] = mapped_column(String(128), index=True)
    device_owner: Mapped[str | None] = mapped_column(String(128), index=True)
    fixed_ips: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    binding_host_id: Mapped[str | None] = mapped_column(String(255), index=True)
    admin_state_up: Mapped[bool | None] = mapped_column(Boolean)
