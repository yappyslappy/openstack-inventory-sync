"""Inventory source model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.models.mixins import TimestampMixin


class InventorySource(TimestampMixin, Base):
    """A locally configured OpenStack project inventory source."""

    __tablename__ = "inventory_sources"
    __table_args__ = (
        UniqueConstraint("scope_key", name="uq_inventory_sources_scope_key"),
        UniqueConstraint(
            "auth_url",
            "region_name",
            "openstack_project_id",
            name="uq_inventory_sources_project_mapping",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scope_key: Mapped[str] = mapped_column(String(128), nullable=False)
    openstack_project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    openstack_project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    region_name: Mapped[str] = mapped_column(String(128), nullable=False)
    auth_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failed_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
