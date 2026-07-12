from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from openstack_inventory_sync.models import Server
from openstack_inventory_sync.repositories.inventory import InventoryRepository


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
) -> None:
    session = sqlite_session_factory()
    repository = InventoryRepository(session)
    first_seen = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)

    inserted = repository.upsert_many(
        Server,
        [server_payload("server-1")],
        region_name="RegionOne",
        seen_at=first_seen,
    )
    session.flush()

    assert inserted.inserted == 1
    assert normalize_sqlite_datetime(session.get(Server, "server-1").first_seen_at) == first_seen

    updated_at = first_seen + timedelta(minutes=5)
    updated = repository.upsert_many(
        Server,
        [server_payload("server-1", name="web-renamed")],
        region_name="RegionOne",
        seen_at=updated_at,
    )
    session.flush()

    row = session.get(Server, "server-1")
    assert updated.updated == 1
    assert row.name == "web-renamed"
    assert normalize_sqlite_datetime(row.first_seen_at) == first_seen
    assert normalize_sqlite_datetime(row.last_seen_at) == updated_at

    deleted_at = updated_at + timedelta(minutes=5)
    deleted = repository.upsert_many(
        Server,
        [],
        region_name="RegionOne",
        seen_at=deleted_at,
    )
    session.flush()

    assert deleted.deleted == 1
    assert row.is_deleted is True
    assert normalize_sqlite_datetime(row.deleted_at) == deleted_at
    session.close()


def test_repository_removes_missing_rows(sqlite_session_factory: sessionmaker[Session]) -> None:
    session = sqlite_session_factory()
    repository = InventoryRepository(session)
    seen_at = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)

    repository.upsert_many(
        Server,
        [server_payload("server-1")],
        region_name="RegionOne",
        seen_at=seen_at,
    )
    session.flush()

    removed = repository.upsert_many(
        Server,
        [],
        region_name="RegionOne",
        seen_at=seen_at,
        remove_missing=True,
    )
    session.flush()

    assert removed.removed == 1
    assert session.get(Server, "server-1") is None
    session.close()
