"""Add multi-project inventory source ownership.

Revision ID: 0002_multi_project
Revises: 0001_initial_inventory_schema
Create Date: 2026-07-12 00:00:00
"""

from __future__ import annotations

import os

import sqlalchemy as sa
from alembic import op

revision = "0002_multi_project"
down_revision = "0001_initial_inventory_schema"
branch_labels = None
depends_on = None

INVENTORY_TABLES = (
    "projects",
    "flavors",
    "images",
    "networks",
    "subnets",
    "ports",
    "servers",
    "volumes",
    "floating_ips",
    "security_groups",
)


def upgrade() -> None:
    bind = op.get_bind()
    existing_rows = _existing_inventory_rows(bind)
    backfill = _read_backfill_environment() if existing_rows else None
    if existing_rows and backfill is None:
        raise RuntimeError(
            "Existing inventory rows require explicit backfill values before migration. "
            "Set INVENTORY_SCOPE, OPENSTACK_PROJECT_ID, OPENSTACK_PROJECT_NAME, "
            "OS_AUTH_URL, and OS_REGION_NAME, then rerun alembic upgrade head."
        )

    op.create_table(
        "inventory_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scope_key", sa.String(length=128), nullable=False),
        sa.Column("openstack_project_id", sa.String(length=128), nullable=False),
        sa.Column("openstack_project_name", sa.String(length=255), nullable=False),
        sa.Column("region_name", sa.String(length=128), nullable=False),
        sa.Column("auth_url", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failed_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_key", name="uq_inventory_sources_scope_key"),
        sa.UniqueConstraint(
            "auth_url",
            "region_name",
            "openstack_project_id",
            name="uq_inventory_sources_project_mapping",
        ),
    )

    for table_name in INVENTORY_TABLES:
        op.add_column(table_name, sa.Column("inventory_source_id", sa.Integer(), nullable=True))

    source_id = _create_backfill_source(bind, backfill) if backfill else None
    if source_id is not None:
        for table_name in INVENTORY_TABLES:
            op.execute(
                sa.text(f"UPDATE {table_name} SET inventory_source_id = :source_id").bindparams(
                    source_id=source_id
                )
            )

    for table_name in INVENTORY_TABLES:
        op.alter_column(
            table_name, "inventory_source_id", existing_type=sa.Integer(), nullable=False
        )
        op.create_foreign_key(
            f"fk_{table_name}_inventory_source_id",
            table_name,
            "inventory_sources",
            ["inventory_source_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.drop_constraint("PRIMARY", table_name, type_="primary")
        op.create_primary_key(f"pk_{table_name}", table_name, ["inventory_source_id", "id"])
        op.create_index(
            f"ix_{table_name}_source_deleted",
            table_name,
            ["inventory_source_id", "is_deleted"],
        )

    _create_child_tables()


def downgrade() -> None:
    op.drop_table("security_group_rules")
    op.drop_table("volume_attachments")
    op.drop_table("server_addresses")
    op.drop_table("server_tags")

    for table_name in reversed(INVENTORY_TABLES):
        op.drop_index(f"ix_{table_name}_source_deleted", table_name=table_name)
        op.drop_constraint(f"fk_{table_name}_inventory_source_id", table_name, type_="foreignkey")
        op.drop_constraint(f"pk_{table_name}", table_name, type_="primary")
        op.create_primary_key("PRIMARY", table_name, ["id"])
        op.drop_column(table_name, "inventory_source_id")

    op.drop_table("inventory_sources")


def _create_child_tables() -> None:
    op.create_table(
        "server_tags",
        sa.Column("inventory_source_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.String(length=128), nullable=False),
        sa.Column("tag", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["inventory_source_id", "server_id"],
            ["servers.inventory_source_id", "servers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("inventory_source_id", "server_id", "tag"),
        sa.UniqueConstraint(
            "inventory_source_id", "server_id", "tag", name="uq_server_tags_source"
        ),
    )
    op.create_table(
        "server_addresses",
        sa.Column("inventory_source_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.String(length=128), nullable=False),
        sa.Column("network_name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=128), nullable=False),
        sa.Column("address_type", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=16), nullable=True),
        sa.Column("mac_address", sa.String(length=64), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["inventory_source_id", "server_id"],
            ["servers.inventory_source_id", "servers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "inventory_source_id", "server_id", "network_name", "address", "address_type"
        ),
        sa.UniqueConstraint(
            "inventory_source_id",
            "server_id",
            "network_name",
            "address",
            "address_type",
            name="uq_server_addresses_source",
        ),
    )
    op.create_table(
        "volume_attachments",
        sa.Column("inventory_source_id", sa.Integer(), nullable=False),
        sa.Column("volume_id", sa.String(length=128), nullable=False),
        sa.Column("attachment_id", sa.String(length=128), nullable=False),
        sa.Column("server_id", sa.String(length=128), nullable=True),
        sa.Column("device", sa.String(length=255), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["inventory_source_id", "volume_id"],
            ["volumes.inventory_source_id", "volumes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("inventory_source_id", "volume_id", "attachment_id"),
        sa.UniqueConstraint(
            "inventory_source_id",
            "volume_id",
            "attachment_id",
            name="uq_volume_attachments_source",
        ),
    )
    op.create_index("ix_volume_attachments_server_id", "volume_attachments", ["server_id"])
    op.create_table(
        "security_group_rules",
        sa.Column("inventory_source_id", sa.Integer(), nullable=False),
        sa.Column("security_group_id", sa.String(length=128), nullable=False),
        sa.Column("rule_id", sa.String(length=128), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=True),
        sa.Column("ethertype", sa.String(length=32), nullable=True),
        sa.Column("protocol", sa.String(length=64), nullable=True),
        sa.Column("port_range_min", sa.String(length=32), nullable=True),
        sa.Column("port_range_max", sa.String(length=32), nullable=True),
        sa.Column("remote_ip_prefix", sa.String(length=128), nullable=True),
        sa.Column("remote_group_id", sa.String(length=128), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["inventory_source_id", "security_group_id"],
            ["security_groups.inventory_source_id", "security_groups.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("inventory_source_id", "security_group_id", "rule_id"),
        sa.UniqueConstraint(
            "inventory_source_id",
            "security_group_id",
            "rule_id",
            name="uq_security_group_rules_source",
        ),
    )
    op.create_index("ix_security_group_rules_direction", "security_group_rules", ["direction"])


def _existing_inventory_rows(bind: sa.Connection) -> int:
    total = 0
    for table_name in INVENTORY_TABLES:
        total += int(bind.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one())
    return total


def _read_backfill_environment() -> dict[str, str] | None:
    required = {
        "scope_key": os.getenv("INVENTORY_SCOPE"),
        "openstack_project_id": os.getenv("OPENSTACK_PROJECT_ID"),
        "openstack_project_name": os.getenv("OPENSTACK_PROJECT_NAME"),
        "auth_url": os.getenv("OS_AUTH_URL"),
        "region_name": os.getenv("OS_REGION_NAME", "RegionOne"),
    }
    if all(required.values()):
        return {key: str(value) for key, value in required.items()}
    return None


def _create_backfill_source(bind: sa.Connection, values: dict[str, str] | None) -> int | None:
    if values is None:
        return None
    bind.execute(
        sa.text("""
            INSERT INTO inventory_sources (
                scope_key,
                openstack_project_id,
                openstack_project_name,
                region_name,
                auth_url,
                is_active,
                created_at,
                updated_at
            )
            VALUES (
                :scope_key,
                :openstack_project_id,
                :openstack_project_name,
                :region_name,
                :auth_url,
                true,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """),
        values,
    )
    return int(
        bind.execute(
            sa.text("SELECT id FROM inventory_sources WHERE scope_key = :scope_key"),
            {"scope_key": values["scope_key"]},
        ).scalar_one()
    )
