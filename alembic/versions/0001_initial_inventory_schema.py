"""Initial inventory schema.

Revision ID: 0001_initial_inventory_schema
Revises:
Create Date: 2026-07-12 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_inventory_schema"
down_revision = None
branch_labels = None
depends_on = None


TABLES = (
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


def common_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("region_name", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("project_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resource_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resource_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def upgrade() -> None:
    op.create_table(
        "projects",
        *common_columns(),
        sa.Column("domain_id", sa.String(length=128), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
    )
    op.create_table(
        "flavors",
        *common_columns(),
        sa.Column("vcpus", sa.Integer(), nullable=True),
        sa.Column("ram_mb", sa.Integer(), nullable=True),
        sa.Column("disk_gb", sa.Integer(), nullable=True),
        sa.Column("ephemeral_gb", sa.Integer(), nullable=True),
        sa.Column("swap_mb", sa.Integer(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=True),
    )
    op.create_table(
        "images",
        *common_columns(),
        sa.Column("visibility", sa.String(length=64), nullable=True),
        sa.Column("container_format", sa.String(length=64), nullable=True),
        sa.Column("disk_format", sa.String(length=64), nullable=True),
        sa.Column("min_disk", sa.Integer(), nullable=True),
        sa.Column("min_ram", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "networks",
        *common_columns(),
        sa.Column("mtu", sa.Integer(), nullable=True),
        sa.Column("admin_state_up", sa.Boolean(), nullable=True),
        sa.Column("is_shared", sa.Boolean(), nullable=True),
        sa.Column("is_router_external", sa.Boolean(), nullable=True),
        sa.Column("provider_network_type", sa.String(length=64), nullable=True),
        sa.Column("provider_physical_network", sa.String(length=128), nullable=True),
        sa.Column("provider_segmentation_id", sa.Integer(), nullable=True),
    )
    op.create_table(
        "subnets",
        *common_columns(),
        sa.Column("network_id", sa.String(length=128), nullable=True),
        sa.Column("cidr", sa.String(length=64), nullable=True),
        sa.Column("ip_version", sa.String(length=16), nullable=True),
        sa.Column("gateway_ip", sa.String(length=64), nullable=True),
        sa.Column("enable_dhcp", sa.Boolean(), nullable=True),
        sa.Column("allocation_pools", sa.JSON(), nullable=True),
        sa.Column("dns_nameservers", sa.JSON(), nullable=True),
    )
    op.create_table(
        "ports",
        *common_columns(),
        sa.Column("network_id", sa.String(length=128), nullable=True),
        sa.Column("mac_address", sa.String(length=64), nullable=True),
        sa.Column("device_id", sa.String(length=128), nullable=True),
        sa.Column("device_owner", sa.String(length=128), nullable=True),
        sa.Column("fixed_ips", sa.JSON(), nullable=True),
        sa.Column("binding_host_id", sa.String(length=255), nullable=True),
        sa.Column("admin_state_up", sa.Boolean(), nullable=True),
    )
    op.create_table(
        "servers",
        *common_columns(),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("flavor_id", sa.String(length=128), nullable=True),
        sa.Column("image_id", sa.String(length=128), nullable=True),
        sa.Column("availability_zone", sa.String(length=128), nullable=True),
        sa.Column("compute_host", sa.String(length=255), nullable=True),
        sa.Column("vm_state", sa.String(length=64), nullable=True),
        sa.Column("power_state", sa.String(length=64), nullable=True),
        sa.Column("addresses", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("launched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "volumes",
        *common_columns(),
        sa.Column("size_gb", sa.Integer(), nullable=True),
        sa.Column("volume_type", sa.String(length=128), nullable=True),
        sa.Column("bootable", sa.Boolean(), nullable=True),
        sa.Column("availability_zone", sa.String(length=128), nullable=True),
        sa.Column("attachments", sa.JSON(), nullable=True),
    )
    op.create_table(
        "floating_ips",
        *common_columns(),
        sa.Column("floating_ip_address", sa.String(length=64), nullable=True),
        sa.Column("fixed_ip_address", sa.String(length=64), nullable=True),
        sa.Column("port_id", sa.String(length=128), nullable=True),
        sa.Column("router_id", sa.String(length=128), nullable=True),
        sa.Column("network_id", sa.String(length=128), nullable=True),
    )
    op.create_table(
        "security_groups",
        *common_columns(),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("security_group_rules", sa.JSON(), nullable=True),
    )
    create_indexes()


def downgrade() -> None:
    for table_name in reversed(TABLES):
        op.drop_table(table_name)


def create_indexes() -> None:
    for table_name in TABLES:
        op.create_index(f"ix_{table_name}_deleted_at", table_name, ["deleted_at"])
        op.create_index(f"ix_{table_name}_is_deleted", table_name, ["is_deleted"])
        op.create_index(f"ix_{table_name}_last_seen_at", table_name, ["last_seen_at"])
        op.create_index(f"ix_{table_name}_name", table_name, ["name"])
        op.create_index(f"ix_{table_name}_project_id", table_name, ["project_id"])
        op.create_index(f"ix_{table_name}_region_name", table_name, ["region_name"])
        op.create_index(f"ix_{table_name}_status", table_name, ["status"])

    op.create_index("ix_projects_domain_id", "projects", ["domain_id"])
    op.create_index("ix_flavors_is_public", "flavors", ["is_public"])
    op.create_index("ix_images_visibility", "images", ["visibility"])
    op.create_index("ix_networks_is_router_external", "networks", ["is_router_external"])
    op.create_index("ix_networks_is_shared", "networks", ["is_shared"])
    op.create_index("ix_subnets_cidr", "subnets", ["cidr"])
    op.create_index("ix_subnets_ip_version", "subnets", ["ip_version"])
    op.create_index("ix_subnets_network_id", "subnets", ["network_id"])
    op.create_index("ix_ports_binding_host_id", "ports", ["binding_host_id"])
    op.create_index("ix_ports_device_id", "ports", ["device_id"])
    op.create_index("ix_ports_device_owner", "ports", ["device_owner"])
    op.create_index("ix_ports_mac_address", "ports", ["mac_address"])
    op.create_index("ix_ports_network_id", "ports", ["network_id"])
    op.create_index("ix_servers_availability_zone", "servers", ["availability_zone"])
    op.create_index("ix_servers_compute_host", "servers", ["compute_host"])
    op.create_index("ix_servers_flavor_id", "servers", ["flavor_id"])
    op.create_index("ix_servers_image_id", "servers", ["image_id"])
    op.create_index("ix_servers_power_state", "servers", ["power_state"])
    op.create_index("ix_servers_user_id", "servers", ["user_id"])
    op.create_index("ix_servers_vm_state", "servers", ["vm_state"])
    op.create_index("ix_volumes_availability_zone", "volumes", ["availability_zone"])
    op.create_index("ix_volumes_bootable", "volumes", ["bootable"])
    op.create_index("ix_volumes_volume_type", "volumes", ["volume_type"])
    op.create_index("ix_floating_ips_fixed_ip_address", "floating_ips", ["fixed_ip_address"])
    op.create_index("ix_floating_ips_floating_ip_address", "floating_ips", ["floating_ip_address"])
    op.create_index("ix_floating_ips_network_id", "floating_ips", ["network_id"])
    op.create_index("ix_floating_ips_port_id", "floating_ips", ["port_id"])
    op.create_index("ix_floating_ips_router_id", "floating_ips", ["router_id"])
