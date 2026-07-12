"""Volume inventory model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.models.mixins import OpenStackResourceMixin


class Volume(OpenStackResourceMixin, Base):
    __tablename__ = "volumes"

    size_gb: Mapped[int | None] = mapped_column(Integer)
    volume_type: Mapped[str | None] = mapped_column(String(128), index=True)
    bootable: Mapped[bool | None] = mapped_column(Boolean, index=True)
    availability_zone: Mapped[str | None] = mapped_column(String(128), index=True)
    attachments: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
