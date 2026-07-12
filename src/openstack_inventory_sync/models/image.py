"""Image inventory model."""

from __future__ import annotations

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.models.mixins import OpenStackResourceMixin


class Image(OpenStackResourceMixin, Base):
    __tablename__ = "images"

    visibility: Mapped[str | None] = mapped_column(String(64), index=True)
    container_format: Mapped[str | None] = mapped_column(String(64))
    disk_format: Mapped[str | None] = mapped_column(String(64))
    min_disk: Mapped[int | None] = mapped_column(Integer)
    min_ram: Mapped[int | None] = mapped_column(Integer)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    checksum: Mapped[str | None] = mapped_column(String(255))
