from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from openstack_inventory_sync.models import Server
from openstack_inventory_sync.sync.servers import ServerSync


class FakeClient:
    def list_servers(self) -> list[dict[str, object]]:
        return [
            {
                "id": "server-1",
                "name": "web-01",
                "project_id": "project-1",
                "status": "ACTIVE",
                "image": {"id": "image-1"},
                "flavor": {"id": "flavor-1"},
            }
        ]


def test_server_sync_fetches_serializes_and_upserts(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    session = sqlite_session_factory()
    result = ServerSync(FakeClient(), "RegionOne").run(session)
    session.flush()

    row = session.get(Server, "server-1")
    assert result.fetched == 1
    assert result.inserted == 1
    assert row is not None
    assert row.flavor_id == "flavor-1"
    session.close()
