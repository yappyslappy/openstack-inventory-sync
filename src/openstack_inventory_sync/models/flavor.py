"""Flavor inventory model."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.models.mixins import OpenStackResourceMixin


class Flavor(OpenStackResourceMixin, Base):
    __tablename__ = "flavors"

    vcpus: Mapped[int | None] = mapped_column(Integer)
    ram_mb: Mapped[int | None] = mapped_column(Integer)
    disk_gb: Mapped[int | None] = mapped_column(Integer)
    ephemeral_gb: Mapped[int | None] = mapped_column(Integer)
    swap_mb: Mapped[int | None] = mapped_column(Integer)
    is_public: Mapped[bool | None] = mapped_column(Boolean, index=True)
