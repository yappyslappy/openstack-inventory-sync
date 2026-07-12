from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import openstack_inventory_sync.models  # noqa: F401
from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.repositories.inventory import InventoryRepository
from openstack_inventory_sync.sync.context import InventorySourceContext


@pytest.fixture()
def sqlite_session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def source_context(sqlite_session_factory: sessionmaker[Session]) -> InventorySourceContext:
    return create_source(sqlite_session_factory, "appdev", "project-appdev", "DF-APPDEV")


@pytest.fixture()
def other_source_context(sqlite_session_factory: sessionmaker[Session]) -> InventorySourceContext:
    return create_source(sqlite_session_factory, "apptest", "project-apptest", "DF-APPTEST")


def create_source(
    session_factory: sessionmaker[Session],
    scope_key: str,
    project_id: str,
    project_name: str,
) -> InventorySourceContext:
    session = session_factory()
    try:
        source = InventoryRepository(session).ensure_inventory_source(
            scope_key=scope_key,
            openstack_project_id=project_id,
            openstack_project_name=project_name,
            region_name="RegionOne",
            auth_url="https://identity.example/v3",
        )
        session.commit()
        return source.context
    finally:
        session.close()
