"""Server inventory model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.models.mixins import OpenStackResourceMixin


class Server(OpenStackResourceMixin, Base):
    __tablename__ = "servers"

    user_id: Mapped[str | None] = mapped_column(String(128), index=True)
    flavor_id: Mapped[str | None] = mapped_column(String(128), index=True)
    image_id: Mapped[str | None] = mapped_column(String(128), index=True)
    availability_zone: Mapped[str | None] = mapped_column(String(128), index=True)
    compute_host: Mapped[str | None] = mapped_column(String(255), index=True)
    vm_state: Mapped[str | None] = mapped_column(String(64), index=True)
    power_state: Mapped[str | None] = mapped_column(String(64), index=True)
    addresses: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    launched_at: Mapped[datetime | None]
    terminated_at: Mapped[datetime | None]
