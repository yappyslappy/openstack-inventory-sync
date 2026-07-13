from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

MAX_ALEMBIC_REVISION_LENGTH = 32
VERSIONS_DIR = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def test_multi_project_migration_metadata() -> None:
    migration = (VERSIONS_DIR / "0002_multi_project_inventory_sources.py").read_text()

    assert 'revision = "0002_multi_project"' in migration
    assert 'down_revision = "0001_initial_inventory_schema"' in migration
    assert "inventory_sources" in migration
    assert "inventory_source_id" in migration
    assert "server_tags" in migration
    assert "volume_attachments" in migration
    assert "security_group_rules" in migration


def test_alembic_revision_graph_is_mysql_version_table_compatible() -> None:
    revisions: dict[str, Path] = {}
    down_revisions: dict[str, set[str]] = {}

    for path in sorted(VERSIONS_DIR.glob("*.py")):
        metadata = read_revision_metadata(path)
        revision = metadata["revision"]
        assert isinstance(revision, str), f"{path.name} revision must be a string"
        assert (
            len(revision) <= MAX_ALEMBIC_REVISION_LENGTH
        ), f"{path.name} revision {revision!r} exceeds {MAX_ALEMBIC_REVISION_LENGTH} characters"
        assert (
            revision not in revisions
        ), f"Duplicate Alembic revision {revision!r} in {path.name} and {revisions[revision].name}"
        revisions[revision] = path
        down_revisions[revision] = normalize_down_revision(metadata["down_revision"])

    for revision, parents in down_revisions.items():
        for parent in parents:
            assert (
                parent in revisions
            ), f"Alembic revision {revision!r} references nonexistent down_revision {parent!r}"


def read_revision_metadata(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(), filename=str(path))
    metadata: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                metadata[target.id] = ast.literal_eval(node.value)

    assert "revision" in metadata, f"{path.name} is missing revision"
    assert "down_revision" in metadata, f"{path.name} is missing down_revision"
    return metadata


def normalize_down_revision(value: object) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value}
    if isinstance(value, tuple | list):
        return {item for item in value if isinstance(item, str)}
    raise AssertionError(f"Unsupported down_revision value: {value!r}")
