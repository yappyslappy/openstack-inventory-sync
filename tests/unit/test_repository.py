from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from sqlalchemy.orm import Session, sessionmaker

from openstack_inventory_sync.exceptions import InventorySourceConflictError
from openstack_inventory_sync.models import Server, ServerAddress, ServerTag
from openstack_inventory_sync.repositories.inventory import InventoryRepository
from openstack_inventory_sync.sync.context import InventorySourceContext


def server_payload(server_id: str, *, name: str = "web-01") -> dict[str, object]:
    return {
        "id": server_id,
        "region_name": "RegionOne",
        "name": name,
        "project_id": "project-1",
        "status": "ACTIVE",
        "raw": {"id": server_id, "name": name},
        "resource_created_at": None,
        "resource_updated_at": None,
        "user_id": "user-1",
        "flavor_id": "flavor-1",
        "image_id": "image-1",
        "availability_zone": "nova",
        "compute_host": "compute-01",
        "vm_state": "active",
        "power_state": "1",
        "addresses": {},
        "metadata_json": {},
        "launched_at": None,
        "terminated_at": None,
    }


def normalize_sqlite_datetime(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def test_repository_inserts_updates_and_soft_deletes(
    sqlite_session_factory: sessionmaker[Session],
    source_context: InventorySourceContext,
) -> None:
    session = sqlite_session_factory()
    repository = InventoryRepository(session)
    first_seen = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)

    inserted = repository.upsert_many(
        Server,
        [server_payload("server-1")],
        source=source_context,
        seen_at=first_seen,
    )
    session.flush()

    assert inserted.inserted == 1
    inserted_row = session.get(Server, (source_context.source_id, "server-1"))
    assert inserted_row is not None
    assert normalize_sqlite_datetime(inserted_row.first_seen_at) == first_seen

    updated_at = first_seen + timedelta(minutes=5)
    updated = repository.upsert_many(
        Server,
        [server_payload("server-1", name="web-renamed")],
        source=source_context,
        seen_at=updated_at,
    )
    session.flush()

    row = session.get(Server, (source_context.source_id, "server-1"))
    assert row is not None
    assert updated.updated == 1
    assert row.name == "web-renamed"
    assert normalize_sqlite_datetime(row.first_seen_at) == first_seen
    assert normalize_sqlite_datetime(row.last_seen_at) == updated_at

    deleted_at = updated_at + timedelta(minutes=5)
    deleted = repository.upsert_many(
        Server,
        [],
        source=source_context,
        seen_at=deleted_at,
    )
    session.flush()

    assert deleted.deleted == 1
    assert row.is_deleted is True
    assert row.deleted_at is not None
    assert normalize_sqlite_datetime(row.deleted_at) == deleted_at
    session.close()


def test_repository_removes_missing_rows(
    sqlite_session_factory: sessionmaker[Session],
    source_context: InventorySourceContext,
) -> None:
    session = sqlite_session_factory()
    repository = InventoryRepository(session)
    seen_at = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)

    repository.upsert_many(
        Server,
        [server_payload("server-1")],
        source=source_context,
        seen_at=seen_at,
    )
    session.flush()

    removed = repository.upsert_many(
        Server,
        [],
        source=source_context,
        seen_at=seen_at,
        remove_missing=True,
    )
    session.flush()

    assert removed.removed == 1
    assert session.get(Server, (source_context.source_id, "server-1")) is None
    session.close()


def test_one_source_soft_delete_does_not_deactivate_another_source(
    sqlite_session_factory: sessionmaker[Session],
    source_context: InventorySourceContext,
    other_source_context: InventorySourceContext,
) -> None:
    session = sqlite_session_factory()
    repository = InventoryRepository(session)
    seen_at = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)

    repository.upsert_many(
        Server,
        [server_payload("server-1", name="appdev-web")],
        source=source_context,
        seen_at=seen_at,
    )
    repository.upsert_many(
        Server,
        [server_payload("server-1", name="apptest-web")],
        source=other_source_context,
        seen_at=seen_at,
    )
    session.flush()

    deleted = repository.upsert_many(
        Server,
        [],
        source=source_context,
        seen_at=seen_at + timedelta(minutes=5),
    )
    session.flush()

    appdev = session.get(Server, (source_context.source_id, "server-1"))
    apptest = session.get(Server, (other_source_context.source_id, "server-1"))
    assert appdev is not None
    assert apptest is not None
    assert deleted.deleted == 1
    assert appdev.is_deleted is True
    assert apptest.is_deleted is False
    assert apptest.name == "apptest-web"
    session.close()


def test_repository_requires_source_context(sqlite_session_factory: sessionmaker[Session]) -> None:
    session = sqlite_session_factory()

    with pytest.raises(InventorySourceConflictError, match="requires an inventory source"):
        InventoryRepository(session).upsert_many(
            Server,
            [server_payload("server-1")],
            source=cast(Any, None),
            seen_at=datetime(2026, 7, 12, 12, 0, tzinfo=UTC),
        )
    session.close()


def test_duplicate_inventory_scope_is_rejected(
    sqlite_session_factory: sessionmaker[Session],
    source_context: InventorySourceContext,
) -> None:
    session = sqlite_session_factory()

    with pytest.raises(InventorySourceConflictError, match="INVENTORY_SCOPE"):
        InventoryRepository(session).ensure_inventory_source(
            scope_key=source_context.scope_key,
            openstack_project_id="different-project",
            openstack_project_name="Different",
            region_name=source_context.region_name,
            auth_url=source_context.auth_url,
        )
    session.close()


def test_duplicate_source_project_mapping_is_rejected(
    sqlite_session_factory: sessionmaker[Session],
    source_context: InventorySourceContext,
) -> None:
    session = sqlite_session_factory()

    with pytest.raises(InventorySourceConflictError, match="different INVENTORY_SCOPE"):
        InventoryRepository(session).ensure_inventory_source(
            scope_key="different-scope",
            openstack_project_id=source_context.openstack_project_id,
            openstack_project_name=source_context.openstack_project_name,
            region_name=source_context.region_name,
            auth_url=source_context.auth_url,
        )
    session.close()


def test_server_child_records_are_source_specific(
    sqlite_session_factory: sessionmaker[Session],
    source_context: InventorySourceContext,
    other_source_context: InventorySourceContext,
) -> None:
    session = sqlite_session_factory()
    repository = InventoryRepository(session)
    seen_at = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)

    for source in (source_context, other_source_context):
        repository.upsert_many(
            Server,
            [server_payload("server-1")],
            source=source,
            seen_at=seen_at,
        )

    repository.replace_child_records(
        ServerTag,
        [{"server_id": "server-1", "tag": "appdev"}],
        source=source_context,
        parent_field="server_id",
        parent_ids={"server-1"},
    )
    repository.replace_child_records(
        ServerAddress,
        [
            {
                "server_id": "server-1",
                "network_name": "private",
                "address": "10.0.0.10",
                "address_type": "fixed",
                "version": "4",
                "mac_address": "fa:16:3e:00:00:01",
                "raw": {"addr": "10.0.0.10"},
            }
        ],
        source=source_context,
        parent_field="server_id",
        parent_ids={"server-1"},
    )
    session.flush()

    assert session.get(ServerTag, (source_context.source_id, "server-1", "appdev")) is not None
    assert session.get(ServerTag, (other_source_context.source_id, "server-1", "appdev")) is None
    assert (
        session.get(
            ServerAddress,
            (source_context.source_id, "server-1", "private", "10.0.0.10", "fixed"),
        )
        is not None
    )
    session.close()
