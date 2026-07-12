from __future__ import annotations

from pathlib import Path


def test_multi_project_migration_metadata() -> None:
    migration = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0002_multi_project_inventory_sources.py"
    ).read_text()

    assert 'down_revision = "0001_initial_inventory_schema"' in migration
    assert "inventory_sources" in migration
    assert "inventory_source_id" in migration
    assert "server_tags" in migration
    assert "volume_attachments" in migration
    assert "security_group_rules" in migration
