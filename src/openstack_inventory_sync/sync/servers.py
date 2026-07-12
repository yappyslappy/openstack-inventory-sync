"""Server synchronization."""

from openstack_inventory_sync.models import Server, ServerAddress, ServerTag
from openstack_inventory_sync.openstack.serializers import (
    serialize_server,
    serialize_server_addresses,
    serialize_server_tags,
)
from openstack_inventory_sync.repositories.inventory import InventoryRepository
from openstack_inventory_sync.sync.base import ResourcePayload, ResourceSync


class ServerSync(ResourceSync):
    resource_name = "servers"
    model = Server
    list_method_name = "list_servers"
    serializer = staticmethod(serialize_server)

    def sync_child_records(
        self, repository: InventoryRepository, accepted: list[ResourcePayload]
    ) -> None:
        parent_ids = {payload["id"] for _, payload in accepted}
        repository.replace_child_records(
            ServerTag,
            [row for resource, _ in accepted for row in serialize_server_tags(resource)],
            source=self.source,
            parent_field="server_id",
            parent_ids=parent_ids,
        )
        repository.replace_child_records(
            ServerAddress,
            [row for resource, _ in accepted for row in serialize_server_addresses(resource)],
            source=self.source,
            parent_field="server_id",
            parent_ids=parent_ids,
        )
