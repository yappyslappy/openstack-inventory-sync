"""Security group inventory model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.models.mixins import OpenStackResourceMixin


class SecurityGroup(OpenStackResourceMixin, Base):
    __tablename__ = "security_groups"

    description: Mapped[str | None] = mapped_column(Text)
    security_group_rules: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
