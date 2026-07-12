"""Network inventory model."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.models.mixins import OpenStackResourceMixin


class Network(OpenStackResourceMixin, Base):
    __tablename__ = "networks"

    mtu: Mapped[int | None] = mapped_column(Integer)
    admin_state_up: Mapped[bool | None] = mapped_column(Boolean)
    is_shared: Mapped[bool | None] = mapped_column(Boolean, index=True)
    is_router_external: Mapped[bool | None] = mapped_column(Boolean, index=True)
    provider_network_type: Mapped[str | None] = mapped_column(String(64))
    provider_physical_network: Mapped[str | None] = mapped_column(String(128))
    provider_segmentation_id: Mapped[int | None] = mapped_column(Integer)
