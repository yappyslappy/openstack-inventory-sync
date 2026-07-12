"""Volume inventory model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKeyConstraint, Integer, String, UniqueConstraint
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


class VolumeAttachment(Base):
    """Normalized volume attachment owned by one inventory source."""

    __tablename__ = "volume_attachments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["inventory_source_id", "volume_id"],
            ["volumes.inventory_source_id", "volumes.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "inventory_source_id",
            "volume_id",
            "attachment_id",
            name="uq_volume_attachments_source",
        ),
    )

    inventory_source_id: Mapped[int] = mapped_column(primary_key=True)
    volume_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    attachment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    server_id: Mapped[str | None] = mapped_column(String(128), index=True)
    device: Mapped[str | None] = mapped_column(String(255))
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
