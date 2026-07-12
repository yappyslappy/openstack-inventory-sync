"""Server inventory model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKeyConstraint, String, UniqueConstraint
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


class ServerTag(Base):
    """Normalized server tag owned by one inventory source."""

    __tablename__ = "server_tags"
    __table_args__ = (
        ForeignKeyConstraint(
            ["inventory_source_id", "server_id"],
            ["servers.inventory_source_id", "servers.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("inventory_source_id", "server_id", "tag", name="uq_server_tags_source"),
    )

    inventory_source_id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tag: Mapped[str] = mapped_column(String(255), primary_key=True)


class ServerAddress(Base):
    """Normalized server address owned by one inventory source."""

    __tablename__ = "server_addresses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["inventory_source_id", "server_id"],
            ["servers.inventory_source_id", "servers.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "inventory_source_id",
            "server_id",
            "network_name",
            "address",
            "address_type",
            name="uq_server_addresses_source",
        ),
    )

    inventory_source_id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    network_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    address: Mapped[str] = mapped_column(String(128), primary_key=True)
    address_type: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[str | None] = mapped_column(String(16))
    mac_address: Mapped[str | None] = mapped_column(String(64))
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
