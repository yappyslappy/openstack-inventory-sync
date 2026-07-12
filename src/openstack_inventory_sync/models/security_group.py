"""Security group inventory model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKeyConstraint, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.models.mixins import OpenStackResourceMixin


class SecurityGroup(OpenStackResourceMixin, Base):
    __tablename__ = "security_groups"

    description: Mapped[str | None] = mapped_column(Text)
    security_group_rules: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)


class SecurityGroupRule(Base):
    """Normalized security group rule owned by one inventory source."""

    __tablename__ = "security_group_rules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["inventory_source_id", "security_group_id"],
            ["security_groups.inventory_source_id", "security_groups.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "inventory_source_id",
            "security_group_id",
            "rule_id",
            name="uq_security_group_rules_source",
        ),
    )

    inventory_source_id: Mapped[int] = mapped_column(primary_key=True)
    security_group_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    direction: Mapped[str | None] = mapped_column(String(32), index=True)
    ethertype: Mapped[str | None] = mapped_column(String(32))
    protocol: Mapped[str | None] = mapped_column(String(64))
    port_range_min: Mapped[str | None] = mapped_column(String(32))
    port_range_max: Mapped[str | None] = mapped_column(String(32))
    remote_ip_prefix: Mapped[str | None] = mapped_column(String(128))
    remote_group_id: Mapped[str | None] = mapped_column(String(128))
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
