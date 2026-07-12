from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from openstack_inventory_sync.models import Server, ServerAddress, ServerTag
from openstack_inventory_sync.sync.context import InventorySourceContext
from openstack_inventory_sync.sync.servers import ServerSync


class FakeClient:
    def list_servers(self) -> list[dict[str, object]]:
        return [
            {
                "id": "server-1",
                "name": "web-01",
                "project_id": "project-appdev",
                "status": "ACTIVE",
                "image": {"id": "image-1"},
                "flavor": {"id": "flavor-1"},
                "tags": ["web", "blue"],
                "addresses": {
                    "private": [
                        {
                            "addr": "10.0.0.10",
                            "OS-EXT-IPS:type": "fixed",
                            "version": 4,
                        }
                    ]
                },
            },
            {
                "id": "server-other-project",
                "name": "should-skip",
                "project_id": "project-apptest",
                "status": "ACTIVE",
            },
        ]


def test_server_sync_fetches_serializes_and_upserts(
    sqlite_session_factory: sessionmaker[Session],
    source_context: InventorySourceContext,
) -> None:
    session = sqlite_session_factory()
    result = ServerSync(FakeClient(), source_context).run(session)
    session.flush()

    row = session.get(Server, (source_context.source_id, "server-1"))
    rejected = session.get(Server, (source_context.source_id, "server-other-project"))
    tag = session.get(ServerTag, (source_context.source_id, "server-1", "web"))
    address = session.get(
        ServerAddress,
        (source_context.source_id, "server-1", "private", "10.0.0.10", "fixed"),
    )
    assert result.fetched == 2
    assert result.inserted == 1
    assert result.rejected == 1
    assert row is not None
    assert rejected is None
    assert row.flavor_id == "flavor-1"
    assert tag is not None
    assert address is not None
    session.close()
